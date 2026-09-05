import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agent.graph import build_graph, route_after_triage, route_after_critic
from src.agent.nodes.triage_agent import triage_agent_node
import src.agent.nodes.root_cause_agent as root_cause_module
import src.agent.nodes.critic_agent as critic_module


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_FILE = str(PROJECT_ROOT / "data" / "raw" / "stg_orders.parquet")
SQL_FILE = str(PROJECT_ROOT / "data" / "queries" / "fct_sales.sql")
LINEAGE_FILE = str(PROJECT_ROOT / "data" / "lineage" / "lineage.json")


def test_route_after_triage_branches():
    assert route_after_triage({"issues": [], "agent_proposed_actions": []}) == "no_issues"
    assert route_after_triage({"issues": [{"rule": "X"}], "escalation_count": 0, "agent_proposed_actions": [{"action": "ESCALATE_UPSTREAM"}]}) == "escalate"
    assert route_after_triage({"issues": [{"rule": "X"}], "requires_human_approval": False, "agent_proposed_actions": [{"action": "AUTO_QUARANTINE"}]}) == "auto_remediate"
    assert route_after_triage({"issues": [{"rule": "X"}], "requires_human_approval": True, "agent_proposed_actions": [{"action": "FLAG_FOR_REVIEW"}]}) == "needs_human_review"


def test_llm_unavailable_fails_closed_to_review(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    result = triage_agent_node({
        "input_file": INPUT_FILE,
        "lineage_file": LINEAGE_FILE,
        "affected_stage": "stg_orders",
        "issues": [{"rule": "PRICE_NON_NEGATIVE", "column": "price", "severity": "HIGH", "count": 3}],
        "route_taken": [],
        "escalation_count": 0,
    })
    assert result["requires_human_approval"] is True
    assert result["route_taken"] == ["needs_human_review"]
    assert result["agent_proposed_actions"][0]["action"] == "FLAG_FOR_REVIEW"
    assert result["agent_proposed_actions"][0]["confidence"] == 0.0


def test_checkpointed_review_resumes_through_graph(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    from src.agent.graph import run_pipeline

    paused = run_pipeline(input_file=INPUT_FILE, sql_file=SQL_FILE, lineage_file=LINEAGE_FILE)
    assert paused["requires_human_approval"] is True
    assert paused["pipeline_status"] == "WAITING_FOR_HUMAN_APPROVAL"

    graph = build_graph()
    config = {"configurable": {"thread_id": paused["run_id"]}}
    graph.update_state(config, {"approval_decision": "reject"})
    resumed = graph.invoke(None, config)
    assert resumed["pipeline_status"] == "APPROVAL_REJECTED"
    assert "approval_rejected" in resumed["route_taken"]


def test_checkpointed_approval_resumes_downstream_nodes(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    from src.agent.graph import run_pipeline

    paused = run_pipeline(input_file=INPUT_FILE, sql_file=SQL_FILE, lineage_file=LINEAGE_FILE)
    graph = build_graph()
    config = {"configurable": {"thread_id": paused["run_id"]}}
    graph.update_state(config, {"approval_decision": "approve"})
    resumed = graph.invoke(None, config)
    assert resumed["pipeline_status"] == "APPROVED"
    assert resumed["sql_changed"] is True
    assert resumed["guardrails_approved"] is True
    assert resumed["route_taken"][-1] == "approval_approved"


def test_medium_only_approval_does_not_quarantine(monkeypatch, tmp_path):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    from src.agent.graph import run_pipeline

    medium_only = tmp_path / "medium_only.csv"
    medium_only.write_text(
        "order_id,customer_id,price,status,order_date\n"
        "ORD_1,,25.00,COMPLETED,2026-09-05\n"
        "ORD_2,CUST_0002,30.00,PENDING,2026-09-05\n",
        encoding="utf-8",
    )
    paused = run_pipeline(input_file=str(medium_only), sql_file=SQL_FILE, lineage_file=LINEAGE_FILE)
    graph = build_graph()
    config = {"configurable": {"thread_id": paused["run_id"]}}
    graph.update_state(config, {"approval_decision": "approve"})
    resumed = graph.invoke(None, config)
    assert resumed["quarantined_rows"] == 0


def test_root_cause_agent_fails_closed(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    from src.agent.nodes.root_cause_agent import root_cause_agent_node

    result = root_cause_agent_node({
        "affected_stage": "stg_orders",
        "upstream_ancestors": ["raw_customers"],
        "issues": [{"rule": "PRICE_NON_NEGATIVE", "column": "price", "severity": "HIGH", "count": 3}],
        "lineage_file": LINEAGE_FILE,
        "input_file": INPUT_FILE,
    })
    assert result["root_cause_stage"] == "raw_customers"
    assert result["upstream_causality_proven"] is False
    assert len(result["root_cause_evidence"]) > 0


def test_critic_agent_fails_closed(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    from src.agent.nodes.critic_agent import critic_agent_node

    result = critic_agent_node({
        "affected_stage": "stg_orders",
        "root_cause_stage": "raw_customers",
        "agent_proposed_actions": [{"issue_id": "PRICE_NON_NEGATIVE:price", "action": "FLAG_FOR_REVIEW", "confidence": 0.0}],
        "issues": [{"rule": "PRICE_NON_NEGATIVE", "column": "price", "severity": "HIGH", "count": 3}],
        "requires_human_approval": True,
        "critic_retry_count": 0,
    })
    assert result["critic_verdict"] == "APPROVED"
    assert result["requires_human_approval"] is True
    assert result["pipeline_status"] == "WAITING_FOR_HUMAN_APPROVAL"


def test_root_cause_agent_with_llm_tool_evidence(monkeypatch):
    """Test A: Root-Cause agent tool execution and structured conclusion vs fallback."""
    monkeypatch.setenv("GEMINI_API_KEY", "mock_key")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    class FakePart:
        def __init__(self, function_call=None):
            self.function_call = function_call

    class FakeCall:
        def __init__(self, name, args):
            self.name = name
            self.args = args

    class FakeCandidate:
        def __init__(self, parts):
            self.content = type("Content", (), {"parts": parts})()

    class FakeResponse:
        def __init__(self, candidate, text=None):
            self.candidates = [candidate]
            self.text = text

    step = 0

    class FakeModels:
        @staticmethod
        def generate_content(model, contents, config=None):
            nonlocal step
            step += 1
            if step == 1:
                call = FakeCall("get_sample_rows", {"column": "price", "condition": "negative"})
                return FakeResponse(FakeCandidate([FakePart(function_call=call)]))
            else:
                call = FakeCall("conclude_root_cause", {
                    "root_cause_stage": "raw_customers",
                    "reasoning": "Upstream vendor dataset raw_customers introduced negative prices.",
                    "causality_proven": True
                })
                return FakeResponse(FakeCandidate([FakePart(function_call=call)]))

    class FakeClient:
        def __init__(self, api_key):
            self.models = FakeModels()

    monkeypatch.setattr(root_cause_module.genai, "Client", FakeClient)

    result = root_cause_module.root_cause_agent_node({
        "affected_stage": "stg_orders",
        "upstream_ancestors": ["raw_customers"],
        "issues": [{"rule": "PRICE_NON_NEGATIVE", "column": "price", "severity": "HIGH", "count": 3}],
        "lineage_file": LINEAGE_FILE,
        "input_file": INPUT_FILE,
    })

    assert result["root_cause_stage"] == "raw_customers"
    assert result["upstream_causality_proven"] is True
    assert len(result["root_cause_evidence"]) > 0
    assert any(item.get("type") == "tool" and item.get("name") == "get_sample_rows" for item in result["root_cause_evidence"])

    # Fallback case without LLM API key
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    fallback_result = root_cause_module.root_cause_agent_node({
        "affected_stage": "stg_orders",
        "upstream_ancestors": ["raw_customers"],
        "issues": [{"rule": "PRICE_NON_NEGATIVE", "column": "price", "severity": "HIGH", "count": 3}],
        "lineage_file": LINEAGE_FILE,
        "input_file": INPUT_FILE,
    })
    assert fallback_result["upstream_causality_proven"] is False


def test_critic_retry_loop_bounded_at_one(monkeypatch):
    """Test B: Bounded critic retry loop (1 retry attempt before requiring human approval)."""
    state_0 = {
        "affected_stage": "stg_orders",
        "root_cause_stage": "stg_orders",
        "agent_proposed_actions": [{"issue_id": "PRICE_NON_NEGATIVE:price", "action": "AUTO_QUARANTINE", "confidence": 0.95}],
        "issues": [{"rule": "PRICE_NON_NEGATIVE", "column": "price", "severity": "HIGH", "count": 3}],
        "requires_human_approval": False,
        "critic_retry_count": 0,
    }

    monkeypatch.setenv("GEMINI_API_KEY", "mock_key")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    class FakeCriticResponse:
        def __init__(self, text):
            self.text = text

    class FakeModels:
        @staticmethod
        def generate_content(model, contents, config=None):
            return FakeCriticResponse('{"verdict": "REVISION_REQUIRED", "reasoning": "Action requires double checking."}')

    class FakeClient:
        def __init__(self, api_key):
            self.models = FakeModels()

    monkeypatch.setattr(critic_module.genai, "Client", FakeClient)

    # Attempt 1: Critic flags revision required
    res_1 = critic_module.critic_agent_node(state_0)
    assert res_1["critic_verdict"] == "REVISION_REQUIRED"
    assert res_1["critic_retry_count"] == 1
    assert res_1["requires_human_approval"] is False

    route_1 = route_after_critic({**state_0, **res_1})
    assert route_1 == "revision_required"

    # Attempt 2: Second call also flags revision required -> forces human review (stops retry loop)
    state_1 = {**state_0, "critic_retry_count": 1}
    res_2 = critic_module.critic_agent_node(state_1)
    assert res_2["critic_verdict"] == "REVISION_REQUIRED"
    assert res_2["critic_retry_count"] == 2
    assert res_2["requires_human_approval"] is True

    route_2 = route_after_critic({**state_1, **res_2})
    assert route_2 == "needs_human_review"

    # Attempt 3: Second call passes with APPROVED -> proceeds to auto remediate
    class FakeApprovedModels:
        @staticmethod
        def generate_content(model, contents, config=None):
            return FakeCriticResponse('{"verdict": "APPROVED", "reasoning": "Revision acceptable."}')

    class FakeApprovedClient:
        def __init__(self, api_key):
            self.models = FakeApprovedModels()

    monkeypatch.setattr(critic_module.genai, "Client", FakeApprovedClient)
    res_approved = critic_module.critic_agent_node(state_1)
    assert res_approved["critic_verdict"] == "APPROVED"
    assert res_approved["critic_retry_count"] == 1
    assert res_approved["requires_human_approval"] is False

    route_approved = route_after_critic({**state_1, **res_approved})
    assert route_approved == "auto_remediate"
