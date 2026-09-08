"""Focused contracts for the agentic stages added to the LangGraph workflow."""

from pathlib import Path

from src.agent.nodes.planning_agent import planning_agent_node
import src.agent.nodes.triage_agent as triage_module
from src.agent.nodes.verify_agent import verify_remediation_node
from src.agent.utils.memory import save_incident_memory, search_similar_incidents


def test_planning_creates_explicit_execution_and_verification_steps(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "")
    monkeypatch.setenv("GEMINI_API_KEY", "")
    result = planning_agent_node({
        "affected_stage": "stg_orders",
        "root_cause_stage": "raw_customers",
        "sql_file": "data/queries/fct_sales.sql",
        "issues": [{"rule": "PRICE_NON_NEGATIVE", "column": "price", "severity": "HIGH"}],
    })
    assert result["plan_risk_level"] == "HIGH"
    assert [step["type"] for step in result["remediation_plan"]] == ["INVESTIGATE", "SQL_HEAL", "QUARANTINE", "VERIFY"]


def test_verification_checks_cleaned_artifact(tmp_path: Path):
    cleaned = tmp_path / "cleaned.csv"
    cleaned.write_text(
        "order_id,customer_id,price,status,order_date\n"
        "ORD_1,CUST_1,25.00,COMPLETED,2026-09-05\n",
        encoding="utf-8",
    )
    result = verify_remediation_node({"input_file": str(cleaned), "issues": [{"rule": "PRICE_NON_NEGATIVE"}]})
    assert result["verification_passed"] is True
    assert result["post_remediation_dq"]["issue_count"] == 0


def test_incident_memory_round_trip(monkeypatch, tmp_path: Path):
    import src.agent.utils.db as db_module
    monkeypatch.setattr(db_module, "_db_path", tmp_path / "test.duckdb")
    db_module.init_schema()
    record = {
        "run_id": "mem-test-1",
        "affected_stage": "stg_orders",
        "issue_keys": ["NOT_NULL:customer_id"],
        "resolution": "quarantine and verify",
    }
    save_incident_memory(record)
    records = search_similar_incidents("customer_id", "NOT_NULL")
    assert len(records) >= 1
    assert records[0]["column_name"] == "customer_id"
    assert records[0]["rule"] == "NOT_NULL"


def test_groq_triage_selects_tools_over_multiple_turns(monkeypatch):
    class FakeCall:
        def __init__(self, name, arguments, call_id):
            self.function = type("Function", (), {"name": name, "arguments": arguments})()
            self.id = call_id

    class FakeMessage:
        def __init__(self, calls):
            self.tool_calls = calls
            self.content = None

        def model_dump(self, **_kwargs):
            return {"role": "assistant", "content": None}

    class FakeCompletions:
        def __init__(self):
            self.turn = 0

        def create(self, **_kwargs):
            self.turn += 1
            if self.turn == 1:
                calls = [FakeCall("get_sample_rows", '{"column":"price","condition":"negative"}', "tool-1")]
            elif self.turn == 2:
                calls = [FakeCall("propose_action", '{"issue_id":"PRICE_NON_NEGATIVE:price","action":"AUTO_QUARANTINE","confidence":0.9,"reasoning":"Evidence confirms negative values."}', "tool-2")]
            else:
                calls = []
            return type("Response", (), {"choices": [type("Choice", (), {"message": FakeMessage(calls)})()]})()

    completions = FakeCompletions()
    fake_client = type("Client", (), {"chat": type("Chat", (), {"completions": completions})()})()
    monkeypatch.setattr(triage_module, "get_llm_provider", lambda: "groq")
    monkeypatch.setattr(triage_module, "get_groq_client", lambda: fake_client)
    result = triage_module.triage_agent_node({
        "input_file": str(Path(__file__).parents[1] / "data" / "raw" / "stg_orders.parquet"),
        "lineage_file": str(Path(__file__).parents[1] / "data" / "lineage" / "lineage.json"),
        "affected_stage": "stg_orders",
        "issues": [{"rule": "PRICE_NON_NEGATIVE", "column": "price", "severity": "LOW", "count": 1}],
        "plan_risk_level": "LOW",
    })
    assert [item["name"] for item in result["agent_tool_calls"]] == ["get_sample_rows", "propose_action"]
    assert result["agent_proposed_actions"][0]["issue_id"] == "PRICE_NON_NEGATIVE:price"
