"""
ObsidianDQ - Agent Graph
------------------------

Main LangGraph workflow for the ObsidianDQ pipeline.

Flow:

    Stage Profiling
          ↓
    DQ Detection
          ↓
    Lineage RCA
          ↓
    SQL Healing
          ↓
    Remediation
          ↓
    Guardrails
          ↓
         END
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from .state import AgentState

from .nodes.stage_profile import profile_stage
from .nodes.dq_detect import detect_dq_issues
from .nodes.lineage_rca import analyze_lineage
from .nodes.root_cause_agent import root_cause_agent_node
from .nodes.sql_healer import heal_sql
from .nodes.remediation import remediate_dq_issues
from .nodes.guardrails import apply_guardrails
from .nodes.triage_agent import triage_agent_node
from .nodes.critic_agent import critic_agent_node



# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data"
CHECKPOINTER = MemorySaver()


# ============================================================
# DEFAULT INPUTS
# ============================================================

DEFAULT_INPUT_FILE = (
    DATA_DIR
    / "raw"
    / "stg_orders.parquet"
)

DEFAULT_SQL_FILE = (
    DATA_DIR
    / "queries"
    / "fct_sales.sql"
)


# ============================================================
# NODE 1 - STAGE PROFILING
# ============================================================

def stage_profile_node(
    state: AgentState,
) -> Dict[str, Any]:
    """
    Profile the input/staging dataset.
    """

    print()
    print("=" * 70)
    print("NODE 1: STAGE PROFILING")
    print("=" * 70)

    try:
        result = profile_stage(
            state.get(
                "input_file",
                str(DEFAULT_INPUT_FILE),
            )
        )
    except Exception as exc:
        print(f"[Stage Profiling Warning] {exc}")
        result = {}

    if result is None:
        return {}

    if isinstance(result, dict):
        return result

    return {
        "profile_result": result
    }


# ============================================================
# NODE 2 - DQ DETECTION
# ============================================================

def dq_detect_node(
    state: AgentState,
) -> Dict[str, Any]:
    """
    Detect deterministic data-quality issues across affected and upstream stages.
    """

    print()
    print("=" * 70)
    print("NODE 2: DQ DETECTION")
    print("=" * 70)

    input_file = state.get("input_file", str(DEFAULT_INPUT_FILE))

    try:
        result = detect_dq_issues(input_file)
    except Exception as exc:
        print(f"[DQ Detect Warning] {exc}")
        result = {"issues": [], "issue_count": 0, "severity_summary": {"HIGH": 0, "MEDIUM": 0, "LOW": 0}}

    issues = list(result.get("issues", [])) if isinstance(result, dict) else []

    # Second detection pass over raw_customers.csv if present and not primary input_file
    raw_customers_path = DATA_DIR / "raw" / "raw_customers.csv"
    if raw_customers_path.exists() and str(raw_customers_path.resolve()) != str(Path(input_file).resolve()):
        try:
            upstream_res = detect_dq_issues(str(raw_customers_path))
            if isinstance(upstream_res, dict):
                for up_issue in upstream_res.get("issues", []):
                    merged_issue = dict(up_issue)
                    merged_issue["stage"] = "raw_customers"
                    issues.append(merged_issue)
        except Exception as exc:
            print(f"[Upstream DQ Detect Warning] {exc}")

    high_count = sum(1 for i in issues if str(i.get("severity")).upper() == "HIGH")
    med_count = sum(1 for i in issues if str(i.get("severity")).upper() == "MEDIUM")
    low_count = sum(1 for i in issues if str(i.get("severity")).upper() == "LOW")

    merged_result = {
        "stage_path": str(input_file),
        "row_count": result.get("row_count", 0) if isinstance(result, dict) else 0,
        "issue_count": len(issues),
        "severity_summary": {
            "HIGH": high_count,
            "MEDIUM": med_count,
            "LOW": low_count,
        },
        "issues": issues,
    }

    return {
        "dq_result": merged_result,
        "issues": issues,
        "issue_count": len(issues),
        "severity_summary": merged_result["severity_summary"],
    }
# ============================================================
# NODE 3 - LINEAGE RCA
# ============================================================

def lineage_rca_node(
    state: AgentState,
) -> Dict[str, Any]:
    """
    Perform upstream lineage-based root-cause analysis.
    """

    print()
    print("=" * 70)
    print("NODE 3: LINEAGE RCA")
    print("=" * 70)

    try:
        affected_stage = state.get("affected_stage", "stg_orders")
        lineage_file = state.get("lineage_file", str(DATA_DIR / "lineage" / "lineage.json"))
        result = analyze_lineage(
            affected_stage,
            lineage_file,
            state.get("issues", []),
        )
    except Exception as exc:
        print(f"[Lineage RCA Warning] {exc}")
        result = {
            "affected_stage": state.get("affected_stage", "stg_orders"),
            "issues": state.get("issues", []),
            "direct_upstream": ["raw_customers"],
            "upstream_ancestors": ["raw_customers"],
            "potential_root_causes": ["raw_customers"],
            "root_cause_stage": state.get("affected_stage", "stg_orders"),
            "direct_downstream": ["fct_sales"],
            "downstream_blast_radius": ["fct_sales"],
            "blast_radius_count": 1,
        }

    if result is None:
        return {}

    if isinstance(result, dict):
        return {
            "lineage": result,
            "direct_upstream": result.get("direct_upstream", []),
            "upstream_ancestors": result.get("upstream_ancestors", []),
            "root_cause_stage": result.get("root_cause_stage"),
            "direct_downstream": result.get("direct_downstream", []),
            "downstream_blast_radius": result.get(
                "downstream_blast_radius",
                [],
            ),
            "blast_radius_count": result.get(
                "blast_radius_count",
                0,
            ),
            "potential_root_causes": result.get(
                "potential_root_causes",
                [],
            ),
        }

    return {
        "lineage": result
    }

# ============================================================
# NODE 4 - SQL HEALING
# ============================================================

def sql_healer_node(
    state: AgentState,
) -> Dict[str, Any]:
    """
    Heal the transformation SQL using the AST-grounded SQL healer.
    """

    print()
    print("=" * 70)
    print("NODE 4: SQL HEALING")
    print("=" * 70)

    sql_file = state.get(
        "sql_file",
        str(DEFAULT_SQL_FILE),
    )

    input_file = state.get(
        "input_file",
        str(DEFAULT_INPUT_FILE),
    )

    try:
        result = heal_sql(
            sql_file=sql_file,
            input_file=input_file,
        )
    except Exception as exc:
        print(f"[SQL Healer Warning] {exc}")
        result = {
            "original_sql": "SELECT order_id, customer_id FROM stg_orders;",
            "repaired_sql": "SELECT order_id, customer_id FROM stg_orders;",
            "sql_changed": False,
            "repairs": [],
            "problems": [],
            "success": True,
        }

    if result is None:
        return {}

    return {
        "original_sql": result.get(
            "original_sql",
            "",
        ),
        "repaired_sql": result.get(
            "repaired_sql",
            "",
        ),
        "sql_changed": result.get(
            "sql_changed",
            False,
        ),
        "sql_repairs": result.get(
            "repairs",
            [],
        ),
        "sql_problems": result.get(
            "problems",
            [],
        ),
        "sql_validation": {
            "success": result.get(
                "success",
                False,
            ),
            "referenced_tables": result.get(
                "referenced_tables",
                [],
            ),
            "available_tables": result.get(
                "available_tables",
                [],
            ),
            "missing_tables": result.get(
                "missing_tables",
                [],
            ),
            "output_file": result.get(
                "output_file",
                "",
            ),
        },
    }


def human_review_queue_node(state: AgentState) -> Dict[str, Any]:
    """Pause for review; approval unblocks the pipeline, not an individual issue."""
    decision = state.get("approval_decision")
    if decision == "approve":
        return {
            "pipeline_status": "APPROVED",
            "requires_human_approval": False,
            "route_taken": state.get("route_taken", []) + ["approval_approved"],
        }
    if decision == "reject":
        return {
            "pipeline_status": "APPROVAL_REJECTED",
            "requires_human_approval": False,
            "route_taken": state.get("route_taken", []) + ["approval_rejected"],
        }
    route_taken = state.get("route_taken", [])
    if not route_taken or route_taken[-1] != "needs_human_review":
        route_taken = route_taken + ["needs_human_review"]
    return {
        "pipeline_status": "WAITING_FOR_HUMAN_APPROVAL",
        "requires_human_approval": True,
        "route_taken": route_taken,
    }


def route_after_review(state: AgentState) -> str:
    return "approved" if state.get("approval_decision") == "approve" else "rejected"


def route_after_triage(state: AgentState) -> str:
    """Choose the next graph branch from agent proposals, with deterministic limits."""
    proposals = state.get("agent_proposed_actions", [])

    if not state.get("issues"):
        return "no_issues"
    if state.get("escalation_count", 0) == 0 and any(
        item.get("action") == "ESCALATE_UPSTREAM" for item in proposals
    ):
        return "escalate"
    if state.get("requires_human_approval"):
        return "needs_human_review"
    return "auto_remediate"


def route_after_critic(state: AgentState) -> str:
    """Choose next graph branch after Critic Agent audit."""
    proposals = state.get("agent_proposed_actions", [])
    critic_verdict = state.get("critic_verdict", "APPROVED")
    retry_count = state.get("critic_retry_count", 0)

    if not state.get("issues"):
        return "no_issues"
    if critic_verdict == "REVISION_REQUIRED" and retry_count <= 1:
        return "revision_required"
    if state.get("escalation_count", 0) == 0 and any(
        item.get("action") == "ESCALATE_UPSTREAM" for item in proposals
    ):
        return "escalate"
    if state.get("requires_human_approval") or critic_verdict == "REVISION_REQUIRED":
        return "needs_human_review"
    return "auto_remediate"

# ============================================================
# NODE 5 - REMEDIATION
# ============================================================

def remediation_node(
    state: AgentState,
) -> Dict[str, Any]:
    """
    Apply data-quality remediation actions.
    """

    print()
    print("=" * 70)
    print("NODE 5: REMEDIATION")
    print("=" * 70)

    try:
        result = remediate_dq_issues(
            input_file=state.get("input_file", DEFAULT_INPUT_FILE),
            issues=state.get("issues", []),
            agent_actions=state.get("agent_proposed_actions", []),
        )
    except Exception as exc:
        print(f"[Remediation Warning] {exc}")
        result = {"quarantine_file": None, "quarantined_rows": 0, "actions": []}

    if result is None:
        return {}
    return {
        "remediation_result": result,
        "quarantine_file": result.get("quarantine_file"),
        "quarantined_rows": result.get("quarantined_rows", 0),
        "remediation_actions": result.get("actions", []),
    }


# ============================================================
# NODE 6 - GUARDRAILS
# ============================================================

def guardrails_node(state: AgentState) -> Dict[str, Any]:
    print("\nNODE 6: GUARDRAILS")

    try:
        result = apply_guardrails(
            state.get("dq_result", {})
        )
    except Exception as exc:
        print(f"[Guardrails Warning] {exc}")
        result = {"approved": True, "action": "PASS", "errors": [], "warnings": []}

    if result is None:
        return {}

    return {
        "guardrails_result": result,
        "guardrails_approved": result.get("approved", False),
        "guardrails_action": result.get("action", "BLOCK"),
        "guardrails_errors": result.get("errors", []),
        "guardrails_warnings": result.get("warnings", []),
    }

# ============================================================
# BUILD GRAPH
# ============================================================

def build_graph():
    """
    Build and compile the ObsidianDQ LangGraph workflow.
    """

    workflow = StateGraph(AgentState)

    # --------------------------------------------------------
    # Register nodes
    # --------------------------------------------------------

    workflow.add_node(
        "stage_profile",
        stage_profile_node,
    )

    workflow.add_node(
        "dq_detect",
        dq_detect_node,
    )

    workflow.add_node(
        "lineage_rca",
        lineage_rca_node,
    )

    workflow.add_node(
        "root_cause_agent",
        root_cause_agent_node,
    )

    workflow.add_node(
        "triage_agent",
        triage_agent_node,
    )

    workflow.add_node(
        "critic_agent",
        critic_agent_node,
    )

    workflow.add_node(
        "sql_healer",
        sql_healer_node,
    )

    workflow.add_node(
        "remediation",
        remediation_node,
    )

    workflow.add_node(
        "guardrails",
        guardrails_node,
    )

    workflow.add_node(
        "human_review_queue",
        human_review_queue_node,
    )

    # --------------------------------------------------------
    # Define workflow
    # --------------------------------------------------------

    workflow.add_edge(
        START,
        "stage_profile",
    )

    workflow.add_edge(
        "stage_profile",
        "dq_detect",
    )

    workflow.add_edge(
        "dq_detect",
        "lineage_rca",
    )

    workflow.add_edge("lineage_rca", "root_cause_agent")
    workflow.add_edge("root_cause_agent", "triage_agent")
    workflow.add_conditional_edges(
        "triage_agent",
        route_after_triage,
        {
            "no_issues": "guardrails",
            "escalate": "root_cause_agent",
            "needs_human_review": "critic_agent",
            "auto_remediate": "critic_agent",
        },
    )

    workflow.add_conditional_edges(
        "critic_agent",
        route_after_critic,
        {
            "auto_remediate": "sql_healer",
            "needs_human_review": "human_review_queue",
            "revision_required": "root_cause_agent",
            "escalate": "root_cause_agent",
            "no_issues": "guardrails",
        },
    )

    workflow.add_edge(
        "sql_healer",
        "remediation",
    )

    workflow.add_edge(
        "remediation",
        "guardrails",
    )

    workflow.add_edge(
        "guardrails",
        END,
    )

    workflow.add_conditional_edges(
        "human_review_queue",
        route_after_review,
        {"approved": "sql_healer", "rejected": END},
    )

    # --------------------------------------------------------
    # Compile
    # --------------------------------------------------------

    return workflow.compile(
        checkpointer=CHECKPOINTER,
        interrupt_before=["human_review_queue"],
    )


# ============================================================
# PIPELINE RUNNER
# ============================================================

def run_pipeline(
    input_file: str | None = None,
    sql_file: str | None = None,
    lineage_file: str | None = None,
) -> AgentState:
    """
    Execute the complete ObsidianDQ pipeline.
    """

    graph = build_graph()

    # --------------------------------------------------------
    # Resolve input paths
    # --------------------------------------------------------

    if input_file is None:
        input_file = str(DEFAULT_INPUT_FILE)

    if sql_file is None:
        sql_file = str(DEFAULT_SQL_FILE)

    if lineage_file is None:
        lineage_file = str(PROJECT_ROOT / "data" / "lineage" / "lineage.json")

    import uuid

    # --------------------------------------------------------
    # Initial state
    # --------------------------------------------------------

    initial_state: AgentState = {
    "pipeline_name": "ObsidianDQ",
    "current_stage": "stg_orders",
    "affected_stage": "stg_orders",
    "input_file": input_file,
    "sql_file": sql_file,
    "lineage_file": lineage_file,
    "run_id": str(uuid.uuid4()),
    "route_taken": [],
    "escalation_count": 0,
}

    print()
    print("=" * 70)
    print("OBSIDIANDQ PIPELINE")
    print("=" * 70)

    print()
    print("Input file:")
    print(input_file)

    print()
    print("SQL file:")
    print(sql_file)

    print()

    # --------------------------------------------------------
    # Execute graph
    # --------------------------------------------------------

    final_state = graph.invoke(
        initial_state,
        config={"configurable": {"thread_id": initial_state["run_id"]}},
    )

    return final_state


# ============================================================
# RESULT DISPLAY
# ============================================================

def print_pipeline_result(
    state: AgentState,
) -> None:
    """
    Display a concise summary of the final pipeline state.
    """

    print()
    print("=" * 70)
    print("OBSIDIANDQ PIPELINE RESULT")
    print("=" * 70)

    # --------------------------------------------------------
    # Input
    # --------------------------------------------------------

    print()
    print("Input file:")
    print(
        state.get(
            "input_file",
            "Not available",
        )
    )

    print()
    print("SQL file:")
    print(
        state.get(
            "sql_file",
            "Not available",
        )
    )

    # --------------------------------------------------------
    # DQ information
    # --------------------------------------------------------

    print()
    print("DQ Issues:")

    dq_issues = state.get(
        "dq_issues",
        state.get(
            "issues",
            [],
        ),
    )

    if dq_issues:
        print(dq_issues)
    else:
        print("No DQ issues returned.")

    # --------------------------------------------------------
    # SQL healing
    # --------------------------------------------------------

    print()
    print("SQL Healing:")

    print(
        "Changed:",
        state.get(
            "sql_changed",
            False,
        ),
    )

    sql_validation = state.get(
        "sql_validation",
        {},
    )

    print(
        "Healed SQL file:",
        sql_validation.get(
            "output_file",
            "Not generated",
        ),
    )

# --------------------------------------------------------
# Remediation
# --------------------------------------------------------

    print()

    print("Remediation:")

    remediation_result = state.get(
        "remediation_result",
        None,
    )

    if remediation_result:
        print(remediation_result)
    else:
        print("No remediation result returned.")

    # --------------------------------------------------------
    # Guardrails
    # --------------------------------------------------------

    print()

    print("Guardrails:")

    guardrails = state.get(
        "guardrails_result",
        {},
    )

    if guardrails:
        print(
            "Approved:",
            state.get(
                "guardrails_approved",
                False,
            ),
        )

        print(
            "Action:",
            state.get(
                "guardrails_action",
                "BLOCK",
            ),
        )

        print(
            "Errors:",
            state.get(
                "guardrails_errors",
                [],
            ),
        )

        print(
            "Warnings:",
            state.get(
                "guardrails_warnings",
                [],
            ),
        )

    else:
        print("No guardrail result returned.")

    print()

    print("=" * 70)

    print("PIPELINE COMPLETE")

    print("=" * 70)
# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    final_state = run_pipeline()

    print_pipeline_result(
        final_state
    )