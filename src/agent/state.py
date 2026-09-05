from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict


class AgentState(TypedDict, total=False):
    """
    Shared state passed between all ObsidianDQ agent nodes.

    The state follows the pipeline:

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
    """

    # =========================================================
    # Pipeline information
    # =========================================================

    pipeline_name: str

    current_stage: str

    affected_stage: str

    input_file: str

    sql_file: str

    lineage_file: str

    # =========================================================
    # Stage profiling
    # =========================================================

    profile: Dict[str, Any]

    row_count: int

    column_count: int

    columns: List[str]

    # =========================================================
    # Data Quality detection
    # =========================================================

    dq_result: Dict[str, Any]

    issues: List[Dict[str, Any]]

    issue_count: int

    severity_summary: Dict[str, int]

    # =========================================================
    # Lineage RCA
    # =========================================================

    lineage: Dict[str, Any]

    direct_upstream: List[str]

    upstream_ancestors: List[str]

    root_cause_stage: Optional[str]

    direct_downstream: List[str]

    downstream_blast_radius: List[str]

    blast_radius_count: int

    potential_root_causes: List[str]

    # =========================================================
    # SQL healing
    # =========================================================

    original_sql: str

    repaired_sql: str

    sql_changed: bool

    sql_repairs: List[Dict[str, str]]

    sql_problems: List[str]

    sql_validation: Dict[str, Any]

    # =========================================================
    # Remediation
    # =========================================================

    remediation_result: Dict[str, Any]

    quarantine_file: Optional[str]

    quarantined_rows: int

    remediation_actions: List[Dict[str, Any]]

    # =========================================================
    # Guardrails
    # =========================================================

    guardrails_result: Dict[str, Any]

    guardrails_approved: bool

    guardrails_action: str

    guardrails_errors: List[str]

    guardrails_warnings: List[str]

    # =========================================================
    # Final pipeline result
    # =========================================================

    pipeline_status: str

    final_result: Dict[str, Any]

    error: Optional[str]


def create_initial_state(
    pipeline_name: str = "ObsidianDQ Phase 1",
    input_file: str = "data/raw/stg_orders.parquet",
    sql_file: str = "data/queries/fct_sales.sql",
    lineage_file: str = "data/lineage/lineage.json",
) -> AgentState:
    """
    Create the initial state for an ObsidianDQ pipeline run.
    """

    return AgentState(
        pipeline_name=pipeline_name,

        current_stage="START",

        affected_stage="",

        input_file=input_file,

        sql_file=sql_file,

        lineage_file=lineage_file,

        profile={},

        row_count=0,

        column_count=0,

        columns=[],

        dq_result={},

        issues=[],

        issue_count=0,

        severity_summary={
            "HIGH": 0,
            "MEDIUM": 0,
            "LOW": 0,
        },

        lineage={},

        direct_upstream=[],

        upstream_ancestors=[],

        root_cause_stage=None,

        direct_downstream=[],

        downstream_blast_radius=[],

        blast_radius_count=0,

        potential_root_causes=[],

        original_sql="",

        repaired_sql="",

        sql_changed=False,

        sql_repairs=[],

        sql_problems=[],

        sql_validation={},

        remediation_result={},

        quarantine_file=None,

        quarantined_rows=0,

        remediation_actions=[],

        guardrails_result={},

        guardrails_approved=False,

        guardrails_action="",

        guardrails_errors=[],

        guardrails_warnings=[],

        pipeline_status="INITIALIZED",

        final_result={},

        error=None,
    )


def print_state_summary(state: AgentState) -> None:
    """
    Print a compact summary of the current agent state.
    """

    print("=" * 60)
    print("OBSIDIAN DQ AGENT STATE")
    print("=" * 60)

    print("Pipeline:", state.get("pipeline_name"))
    print("Current stage:", state.get("current_stage"))
    print("Affected stage:", state.get("affected_stage"))

    print()

    print("Input file:", state.get("input_file"))
    print("SQL file:", state.get("sql_file"))
    print("Lineage file:", state.get("lineage_file"))

    print()

    print("Rows:", state.get("row_count"))
    print("Columns:", state.get("column_count"))

    print()

    print("DQ issues:", state.get("issue_count"))

    print(
        "Severity:",
        state.get(
            "severity_summary",
            {
                "HIGH": 0,
                "MEDIUM": 0,
                "LOW": 0,
            },
        ),
    )

    print()

    print("Root cause:", state.get("root_cause_stage"))

    print(
        "Blast radius:",
        state.get("downstream_blast_radius"),
    )

    print()

    print("SQL changed:", state.get("sql_changed"))

    print(
        "Quarantined rows:",
        state.get("quarantined_rows"),
    )

    print()

    print(
        "Guardrails approved:",
        state.get("guardrails_approved"),
    )

    print(
        "Pipeline status:",
        state.get("pipeline_status"),
    )

    print("=" * 60)


# =============================================================
# Standalone test
# =============================================================

if __name__ == "__main__":

    state = create_initial_state()

    print_state_summary(state)