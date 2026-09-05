import json
import sys
from pathlib import Path
from typing import Any, Dict

import pandas as pd
import streamlit as st


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "stg_orders.parquet"
)

SQL_FILE = (
    PROJECT_ROOT
    / "data"
    / "queries"
    / "fct_sales.sql"
)

LINEAGE_FILE = (
    PROJECT_ROOT
    / "data"
    / "lineage"
    / "lineage.json"
)

QUARANTINE_FILE = (
    PROJECT_ROOT
    / "data"
    / "quarantine"
    / "stg_orders_quarantine.parquet"
)


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="ObsidianDQ",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>

    .main-title {
        font-size: 42px;
        font-weight: 700;
        margin-bottom: 0;
    }

    .subtitle {
        font-size: 18px;
        opacity: 0.75;
        margin-bottom: 25px;
    }

    .section-title {
        font-size: 25px;
        font-weight: 650;
        margin-top: 25px;
        margin-bottom: 15px;
    }

    .status-box {
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 15px;
    }

    .small-text {
        font-size: 14px;
        opacity: 0.7;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# IMPORT PIPELINE
# ============================================================

try:
    from src.agent.graph import run_pipeline

    PIPELINE_AVAILABLE = True

except Exception as exc:
    run_pipeline = None
    PIPELINE_AVAILABLE = False
    PIPELINE_IMPORT_ERROR = str(exc)


# ============================================================
# SESSION STATE
# ============================================================

if "pipeline_result" not in st.session_state:
    st.session_state.pipeline_result = None


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def read_text_file(path: Path) -> str:
    """Read a text file safely."""

    if not path.exists():
        return ""

    try:
        return path.read_text(
            encoding="utf-8"
        )
    except Exception:
        return ""


def load_json_file(path: Path) -> Dict[str, Any]:
    """Load JSON safely."""

    if not path.exists():
        return {}

    try:
        with path.open(
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        if isinstance(data, dict):
            return data

        return {}

    except Exception:
        return {}


def load_parquet_file(path: Path):
    """Load parquet safely."""

    if not path.exists():
        return None

    try:
        return pd.read_parquet(path)

    except Exception:
        return None


def get_state_value(
    state: Dict[str, Any],
    key: str,
    default=None,
):
    """Safely retrieve a pipeline state value."""

    if not isinstance(state, dict):
        return default

    return state.get(
        key,
        default,
    )


def normalize_issue_table(issues):
    """Convert DQ issues into a DataFrame."""

    if not issues:
        return pd.DataFrame(
            columns=[
                "rule",
                "column",
                "issue",
                "count",
                "severity",
            ]
        )

    return pd.DataFrame(issues)


def build_lineage_dot(lineage):
    """
    Convert common lineage JSON structures
    into Graphviz DOT.
    """

    nodes = set()
    edges = []

    # --------------------------------------------------------
    # Format 1:
    # {
    #   "nodes": [...],
    #   "edges": [...]
    # }
    # --------------------------------------------------------

    if isinstance(lineage, dict):

        raw_nodes = lineage.get(
            "nodes",
            [],
        )

        raw_edges = lineage.get(
            "edges",
            [],
        )

        if isinstance(raw_nodes, list):

            for node in raw_nodes:

                if isinstance(node, str):
                    nodes.add(node)

                elif isinstance(node, dict):

                    name = (
                        node.get("id")
                        or node.get("name")
                        or node.get("stage")
                    )

                    if name:
                        nodes.add(str(name))

        if isinstance(raw_edges, list):

            for edge in raw_edges:

                if isinstance(edge, dict):

                    source = (
                        edge.get("source")
                        or edge.get("from")
                        or edge.get("upstream")
                    )

                    target = (
                        edge.get("target")
                        or edge.get("to")
                        or edge.get("downstream")
                    )

                    if source and target:

                        source = str(source)
                        target = str(target)

                        nodes.add(source)
                        nodes.add(target)

                        edges.append(
                            (source, target)
                        )

                elif isinstance(edge, (list, tuple)):

                    if len(edge) >= 2:

                        source = str(edge[0])
                        target = str(edge[1])

                        nodes.add(source)
                        nodes.add(target)

                        edges.append(
                            (source, target)
                        )

    # --------------------------------------------------------
    # Format 2:
    # {
    #   "upstream": {
    #       "stg_orders": ["raw_customers"]
    #   }
    # }
    # --------------------------------------------------------

    upstream = lineage.get(
        "upstream",
        {},
    ) if isinstance(lineage, dict) else {}

    if isinstance(upstream, dict):

        for target, sources in upstream.items():

            target = str(target)
            nodes.add(target)

            if isinstance(sources, str):
                sources = [sources]

            if isinstance(sources, list):

                for source in sources:

                    source = str(source)

                    nodes.add(source)

                    edges.append(
                        (source, target)
                    )

    # --------------------------------------------------------
    # Format 3:
    # {
    #   "downstream": {
    #       "raw_customers": ["stg_orders"]
    #   }
    # }
    # --------------------------------------------------------

    downstream = lineage.get(
        "downstream",
        {},
    ) if isinstance(lineage, dict) else {}

    if isinstance(downstream, dict):

        for source, targets in downstream.items():

            source = str(source)
            nodes.add(source)

            if isinstance(targets, str):
                targets = [targets]

            if isinstance(targets, list):

                for target in targets:

                    target = str(target)

                    nodes.add(target)

                    edges.append(
                        (source, target)
                    )

    # --------------------------------------------------------
    # Remove duplicate edges
    # --------------------------------------------------------

    edges = list(
        dict.fromkeys(edges)
    )

    # --------------------------------------------------------
    # Fallback for our expected pipeline
    # --------------------------------------------------------

    if not edges:

        nodes.update(
            [
                "raw_customers",
                "stg_orders",
                "fct_sales",
            ]
        )

        edges = [
            (
                "raw_customers",
                "stg_orders",
            ),
            (
                "stg_orders",
                "fct_sales",
            ),
        ]

    # --------------------------------------------------------
    # Build DOT
    # --------------------------------------------------------

    dot_lines = [
        "digraph G {",
        'rankdir=LR;',
        'node [shape=box, style="rounded,filled", '
        'fontname="Arial"];',
        'edge [penwidth=2];',
    ]

    for node in sorted(nodes):

        safe_node = (
            node.replace('"', "")
        )

        if safe_node == "stg_orders":

            dot_lines.append(
                f'"{safe_node}" '
                '[label="stg_orders\\nAffected Stage", '
                'fillcolor="lightyellow"];'
            )

        else:

            dot_lines.append(
                f'"{safe_node}" '
                f'[label="{safe_node}"];'
            )

    for source, target in edges:

        dot_lines.append(
            f'"{source}" -> "{target}";'
        )

    dot_lines.append("}")

    return "\n".join(dot_lines)


def run_obsidiandq():
    """Execute the real ObsidianDQ pipeline."""

    if not PIPELINE_AVAILABLE:
        raise RuntimeError(
            "ObsidianDQ pipeline could not be imported:\n"
            + PIPELINE_IMPORT_ERROR
        )

    result = run_pipeline(
        input_file=str(INPUT_FILE),
        sql_file=str(SQL_FILE),
    )

    if result is None:
        return {}

    if isinstance(result, dict):
        return result

    return dict(result)


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="main-title">🛡️ ObsidianDQ</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="subtitle">'
    "Deterministic & Agentic Data Quality, "
    "Observability, and Self-Healing Engine"
    "</div>",
    unsafe_allow_html=True,
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header("Pipeline Control")

    st.write(
        "Run the complete ObsidianDQ "
        "data-quality pipeline."
    )

    if st.button(
        "▶ Run ObsidianDQ Pipeline",
        use_container_width=True,
        type="primary",
    ):

        with st.spinner(
            "Running ObsidianDQ pipeline..."
        ):

            try:

                result = run_obsidiandq()

                st.session_state.pipeline_result = result

                st.success(
                    "Pipeline completed successfully."
                )

            except Exception as exc:

                st.session_state.pipeline_result = None

                st.error(
                    "Pipeline execution failed."
                )

                st.exception(exc)

    st.divider()

    st.subheader("Input")

    st.caption(
        str(INPUT_FILE)
    )

    st.subheader("SQL")

    st.caption(
        str(SQL_FILE)
    )

    st.subheader("Lineage")

    st.caption(
        str(LINEAGE_FILE)
    )


# ============================================================
# LOAD PIPELINE STATE
# ============================================================

state = st.session_state.pipeline_result


# ============================================================
# INITIAL SCREEN
# ============================================================

if not state:

    st.info(
        "Click **Run ObsidianDQ Pipeline** "
        "in the sidebar to execute the real "
        "pipeline and populate the dashboard."
    )

    if not PIPELINE_AVAILABLE:

        st.error(
            "The backend pipeline could not be imported."
        )

        st.code(
            PIPELINE_IMPORT_ERROR
        )

    else:

        st.success(
            "Backend pipeline is available."
        )

    st.stop()


# ============================================================
# EXTRACT STATE
# ============================================================

issues = get_state_value(
    state,
    "issues",
    [],
)

dq_result = get_state_value(
    state,
    "dq_result",
    {},
)

severity_summary = get_state_value(
    state,
    "severity_summary",
    {},
)

high_count = (
    severity_summary.get("HIGH", 0)
    if isinstance(severity_summary, dict)
    else 0
)

row_count = get_state_value(
    state,
    "row_count",
    dq_result.get(
        "row_count",
        0,
    ) if isinstance(dq_result, dict) else 0,
)

issue_count = get_state_value(
    state,
    "issue_count",
    len(issues),
)

affected_stage = get_state_value(
    state,
    "affected_stage",
    "stg_orders",
)

root_cause_stage = get_state_value(
    state,
    "root_cause_stage",
    "",
)

direct_upstream = get_state_value(
    state,
    "direct_upstream",
    [],
)

upstream_ancestors = get_state_value(
    state,
    "upstream_ancestors",
    [],
)

direct_downstream = get_state_value(
    state,
    "direct_downstream",
    [],
)

downstream_blast_radius = get_state_value(
    state,
    "downstream_blast_radius",
    [],
)

blast_radius_count = get_state_value(
    state,
    "blast_radius_count",
    len(downstream_blast_radius),
)

original_sql = get_state_value(
    state,
    "original_sql",
    read_text_file(SQL_FILE),
)

repaired_sql = get_state_value(
    state,
    "repaired_sql",
    "",
)

sql_changed = get_state_value(
    state,
    "sql_changed",
    False,
)

sql_repairs = get_state_value(
    state,
    "sql_repairs",
    [],
)

sql_problems = get_state_value(
    state,
    "sql_problems",
    [],
)

sql_validation = get_state_value(
    state,
    "sql_validation",
    {},
)

remediation_result = get_state_value(
    state,
    "remediation_result",
    {},
)

quarantine_file = get_state_value(
    state,
    "quarantine_file",
    "",
)

quarantined_rows = get_state_value(
    state,
    "quarantined_rows",
    0,
)

guardrails_result = get_state_value(
    state,
    "guardrails_result",
    {},
)

guardrails_approved = get_state_value(
    state,
    "guardrails_approved",
    False,
)

guardrails_action = get_state_value(
    state,
    "guardrails_action",
    "BLOCK",
)

guardrails_errors = get_state_value(
    state,
    "guardrails_errors",
    [],
)

guardrails_warnings = get_state_value(
    state,
    "guardrails_warnings",
    [],
)


# ============================================================
# LOAD FILE DATA
# ============================================================

stage_df = load_parquet_file(
    INPUT_FILE
)

quarantine_df = None

if quarantine_file:

    quarantine_path = Path(
        quarantine_file
    )

    if not quarantine_path.is_absolute():

        quarantine_path = (
            PROJECT_ROOT
            / quarantine_path
        )

    quarantine_df = load_parquet_file(
        quarantine_path
    )

elif QUARANTINE_FILE.exists():

    quarantine_df = load_parquet_file(
        QUARANTINE_FILE
    )


# ============================================================
# PIPELINE OVERVIEW
# ============================================================

st.markdown(
    '<div class="section-title">'
    "Pipeline Overview"
    '</div>',
    unsafe_allow_html=True,
)

if not guardrails_approved:
    pipeline_status = "BLOCKED"
elif high_count > 0:
    pipeline_status = "ATTENTION"
else:
    pipeline_status = "HEALTHY"
col1, col2, col3, col4 = st.columns(4)

with col1:

    st.metric(
        "Pipeline Status",
        pipeline_status,
    )

with col2:

    st.metric(
        "Total Rows",
        row_count,
    )

with col3:

    st.metric(
        "DQ Issues",
        issue_count,
    )

with col4:

    st.metric(
        "Quarantined",
        quarantined_rows,
    )


# ============================================================
# SEVERITY SUMMARY
# ============================================================

st.markdown(
    '<div class="section-title">'
    "DQ Severity Summary"
    "</div>",
    unsafe_allow_html=True,
)

high_count = severity_summary.get(
    "HIGH",
    0,
)

medium_count = severity_summary.get(
    "MEDIUM",
    0,
)

low_count = severity_summary.get(
    "LOW",
    0,
)

col1, col2, col3 = st.columns(3)

with col1:

    st.metric(
        "HIGH",
        high_count,
    )

with col2:

    st.metric(
        "MEDIUM",
        medium_count,
    )

with col3:

    st.metric(
        "LOW",
        low_count,
    )


# ============================================================
# DQ ISSUES
# ============================================================

st.markdown(
    '<div class="section-title">'
    "Detected Data Quality Issues"
    "</div>",
    unsafe_allow_html=True,
)

issues_df = normalize_issue_table(
    issues
)

if not issues_df.empty:

    st.dataframe(
        issues_df,
        use_container_width=True,
        hide_index=True,
    )

else:

    st.success(
        "No data-quality issues detected."
    )


# ============================================================
# STAGE PROFILE
# ============================================================

st.markdown(
    '<div class="section-title">'
    "Stage Profile"
    "</div>",
    unsafe_allow_html=True,
)

profile = get_state_value(
    state,
    "profile",
    {},
)

columns = get_state_value(
    state,
    "columns",
    [],
)

row_count = get_state_value(
    state,
    "row_count",
    0,
)

column_count = get_state_value(
    state,
    "column_count",
    len(columns) if columns else 0,
)

# ------------------------------------------------------------
# PROFILE SUMMARY
# ------------------------------------------------------------

profile_col1, profile_col2, profile_col3 = st.columns(3)

with profile_col1:
    st.metric(
        "Rows",
        row_count,
    )

with profile_col2:
    st.metric(
        "Columns",
        column_count,
    )

with profile_col3:
    st.metric(
        "Profile Status",
        "AVAILABLE" if profile else "BASIC",
    )

# ------------------------------------------------------------
# COLUMN INFORMATION
# ------------------------------------------------------------

if columns:

    st.write(
        "**Columns**"
    )

    display_columns = []

    for item in columns:

        if isinstance(item, str):
            display_columns.append(item)

        elif isinstance(item, dict):
            display_columns.append(
                item.get(
                    "column",
                    item.get(
                        "name",
                        "Unknown"
                    )
                )
            )

        else:
            display_columns.append(
                str(item)
            )

    st.dataframe(
        pd.DataFrame(
            {
                "Column": display_columns
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

# ------------------------------------------------------------
# DETAILED PROFILE
# ------------------------------------------------------------

if profile:

    st.write(
        "**Detailed Profile**"
    )

    # Handle dictionary-style profiling information
    if isinstance(profile, dict):

        profile_rows = []

        for column, details in profile.items():

            if isinstance(details, dict):

                row = {
                    "Column": column,
                    **details,
                }

            else:

                row = {
                    "Column": column,
                    "Profile": details,
                }

            profile_rows.append(row)

        if profile_rows:

            st.dataframe(
                pd.DataFrame(profile_rows),
                use_container_width=True,
                hide_index=True,
            )

    else:

        st.write(profile)

else:

    st.info(
        "Detailed column profiling is unavailable, "
        "but stage-level statistics are available above."
    )

# ============================================================
# LINEAGE
# ============================================================

st.markdown(
    '<div class="section-title">'
    "Data Lineage"
    "</div>",
    unsafe_allow_html=True,
)

lineage = load_json_file(
    LINEAGE_FILE
)

if lineage:

    dot = build_lineage_dot(
        lineage
    )

    st.graphviz_chart(
        dot,
        use_container_width=True,
    )

else:

    st.warning(
        "lineage.json was not found."
    )


# ============================================================
# RCA
# ============================================================

st.markdown(
    '<div class="section-title">'
    "Root Cause Analysis"
    "</div>",
    unsafe_allow_html=True,
)

rca_col1, rca_col2, rca_col3 = st.columns(3)

with rca_col1:

    st.metric(
        "Affected Stage",
        affected_stage,
    )

with rca_col2:

    st.metric(
        "Root Cause",
        root_cause_stage
        or affected_stage,
    )

with rca_col3:

    st.metric(
        "Blast Radius",
        blast_radius_count,
    )


rca_col1, rca_col2 = st.columns(2)

with rca_col1:

    st.write(
        "**Direct Upstream**"
    )

    if direct_upstream:

        for stage in direct_upstream:

            st.write(
                f"← {stage}"
            )

    else:

        st.write(
            "None"
        )

    st.write(
        "**Upstream Ancestors**"
    )

    if upstream_ancestors:

        for stage in upstream_ancestors:

            st.write(
                f"← {stage}"
            )

    else:

        st.write(
            "None"
        )


with rca_col2:

    st.write(
        "**Direct Downstream**"
    )

    if direct_downstream:

        for stage in direct_downstream:

            st.write(
                f"→ {stage}"
            )

    else:

        st.write(
            "None"
        )

    st.write(
        "**Downstream Blast Radius**"
    )

    if downstream_blast_radius:

        for stage in downstream_blast_radius:

            st.write(
                f"→ {stage}"
            )

    else:

        st.write(
            "None"
        )


# ============================================================
# SQL SELF-HEALING
# ============================================================

st.markdown(
    '<div class="section-title">'
    "SQL Self-Healing"
    "</div>",
    unsafe_allow_html=True,
)

sql_col1, sql_col2 = st.columns(2)

with sql_col1:

    st.write(
        "**Original SQL**"
    )

    st.code(
        original_sql
        or "-- Original SQL unavailable",
        language="sql",
    )


with sql_col2:

    st.write(
        "**Repaired SQL**"
    )

    if repaired_sql:

        st.code(
            repaired_sql,
            language="sql",
        )

    else:

        st.info(
            "No repaired SQL returned."
        )


if sql_changed:

    st.success(
        "SQL was modified by the "
        "self-healing engine."
    )

else:

    st.info(
        "No SQL changes were required."
    )


if sql_repairs:

    st.write(
        "**Repairs Applied**"
    )

    st.dataframe(
        pd.DataFrame(sql_repairs),
        use_container_width=True,
        hide_index=True,
    )


if sql_problems:

    st.write(
        "**SQL Problems Detected**"
    )

    for problem in sql_problems:

        st.warning(
            str(problem)
        )


healed_output = (
    sql_validation.get(
        "output_file",
        "",
    )
    if isinstance(
        sql_validation,
        dict,
    )
    else ""
)

if healed_output:

    st.caption(
        f"Healed SQL file: {healed_output}"
    )


# ============================================================
# SQL VALIDATION
# ============================================================

if isinstance(
    sql_validation,
    dict,
) and sql_validation:

    with st.expander(
        "SQL Validation Details"
    ):

        st.json(
            sql_validation
        )


# ============================================================
# REMEDIATION
# ============================================================

st.markdown(
    '<div class="section-title">'
    "Remediation"
    "</div>",
    unsafe_allow_html=True,
)

if remediation_result:

    actions = remediation_result.get(
        "actions",
        [],
    )

    if actions:

        remediation_rows = []

        for action in actions:

            remediation_rows.append(
                {
                    "Severity": action.get(
                        "severity",
                        "",
                    ),
                    "Rule": action.get(
                        "rule",
                        "",
                    ),
                    "Column": action.get(
                        "column",
                        "",
                    ),
                    "Action": action.get(
                        "action",
                        "",
                    ),
                    "Rows Affected": action.get(
                        "rows_affected",
                        0,
                    ),
                }
            )

        st.dataframe(
            pd.DataFrame(
                remediation_rows
            ),
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.info(
            "No remediation actions."
        )

else:

    st.info(
        "No remediation result available."
    )


# ============================================================
# QUARANTINE
# ============================================================

st.markdown(
    '<div class="section-title">'
    "Quarantine"
    "</div>",
    unsafe_allow_html=True,
)

if quarantined_rows > 0:

    st.warning(
        f"{quarantined_rows} rows were quarantined."
    )

    if quarantine_df is not None:

        st.dataframe(
            quarantine_df,
            use_container_width=True,
            hide_index=True,
        )

    if quarantine_file:

        st.caption(
            f"Quarantine file: {quarantine_file}"
        )

else:

    st.success(
        "No rows were quarantined."
    )


# ============================================================
# GUARDRAILS
# ============================================================

st.markdown(
    '<div class="section-title">'
    "Guardrails"
    "</div>",
    unsafe_allow_html=True,
)

guard_col1, guard_col2 = st.columns(2)

with guard_col1:

    st.metric(
        "Approval",
        "APPROVED"
        if guardrails_approved
        else "BLOCKED",
    )

with guard_col2:

    st.metric(
        "Action",
        guardrails_action,
    )


if guardrails_errors:

    st.error(
        "Guardrail Errors"
    )

    for error in guardrails_errors:

        st.write(
            f"• {error}"
        )

elif guardrails_approved:

    st.success(
        "Guardrails approved the pipeline."
    )


if guardrails_warnings:

    st.warning(
        "Guardrail Warnings"
    )

    for warning in guardrails_warnings:

        st.write(
            f"• {warning}"
        )


# ============================================================
# RAW PIPELINE STATE
# ============================================================

with st.expander(
    "View Complete AgentState"
):

    st.json(
        state
    )


# ============================================================
# DATA PREVIEW
# ============================================================

if stage_df is not None:

    st.markdown(
        '<div class="section-title">'
        "Stage Data Preview"
        "</div>",
        unsafe_allow_html=True,
    )

    st.dataframe(
        stage_df.head(20),
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# FOOTER
# ============================================================

st.markdown("---")

st.caption(
    "ObsidianDQ — Deterministic & Agentic "
    "Data Quality, Observability, and "
    "Self-Healing Engine"
)