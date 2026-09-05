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

from .state import AgentState

from .nodes.stage_profile import profile_stage
from .nodes.dq_detect import detect_dq_issues
from .nodes.lineage_rca import analyze_lineage
from .nodes.sql_healer import heal_sql
from .nodes.remediation import remediate_dq_issues
from .nodes.guardrails import apply_guardrails



# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data"


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

    result = profile_stage(
    state.get(
        "input_file",
        str(DEFAULT_INPUT_FILE),
    )
)

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
    Detect deterministic data-quality issues.
    """

    print()
    print("=" * 70)
    print("NODE 2: DQ DETECTION")
    print("=" * 70)

    result = detect_dq_issues(
        state.get(
            "input_file",
            str(DEFAULT_INPUT_FILE),
        )
    )

    if result is None:
        return {}

    if isinstance(result, dict):
        return {
            "dq_result": result,
            "issues": result.get("issues", []),
            "issue_count": result.get("issue_count", 0),
            "severity_summary": result.get(
                "severity_summary",
                {
                    "HIGH": 0,
                    "MEDIUM": 0,
                    "LOW": 0,
                },
            ),
        }

    return {
        "dq_result": result
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

    result = analyze_lineage(
        state["affected_stage"],
        state["lineage_file"],
        state.get("issues", []),
    )

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

    result = heal_sql(
        sql_file=sql_file,
        input_file=input_file,
    )

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

    result = remediate_dq_issues(
    input_file=state.get("input_file", DEFAULT_INPUT_FILE),
    issues=state.get("issues", []),
)


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

    result = apply_guardrails(
        state.get("dq_result", {})
    )

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

    workflow.add_edge(
        "lineage_rca",
        "sql_healer",
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

    # --------------------------------------------------------
    # Compile
    # --------------------------------------------------------

    return workflow.compile()


# ============================================================
# PIPELINE RUNNER
# ============================================================

def run_pipeline(
    input_file: str | None = None,
    sql_file: str | None = None,
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

    # --------------------------------------------------------
    # Initial state
    # --------------------------------------------------------

    initial_state: AgentState = {
    "pipeline_name": "ObsidianDQ",
    "current_stage": "stg_orders",
    "affected_stage": "stg_orders",
    "input_file": input_file,
    "sql_file": sql_file,
    "lineage_file": "data/lineage/lineage.json",
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
        initial_state
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