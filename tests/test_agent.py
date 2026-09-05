from pathlib import Path

import pandas as pd


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

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


# ============================================================
# TEST 1 — INPUT DATA
# ============================================================

def test_input_file_exists():
    """Verify the staging Parquet file exists."""

    assert INPUT_FILE.exists()


def test_input_data_can_be_loaded():
    """Verify the staging data can be loaded."""

    df = pd.read_parquet(INPUT_FILE)

    assert len(df) > 0
    assert len(df.columns) > 0


# ============================================================
# TEST 2 — DQ DETECTION
# ============================================================

def test_dq_detection():
    """Verify DQ detector identifies the injected issues."""

    from src.agent.nodes.dq_detect import detect_dq_issues

    result = detect_dq_issues(
        str(INPUT_FILE)
    )

    assert isinstance(result, dict)

    assert result["row_count"] == 500

    assert result["issue_count"] >= 1

    assert "issues" in result

    assert isinstance(
        result["issues"],
        list,
    )


# ============================================================
# TEST 3 — LINEAGE RCA
# ============================================================

def test_lineage_rca():
    """Verify lineage RCA returns upstream/downstream information."""

    from src.agent.nodes.lineage_rca import analyze_lineage

    result = analyze_lineage(
        "stg_orders",
        str(LINEAGE_FILE),
        [],
    )

    assert isinstance(result, dict)

    assert result["affected_stage"] == "stg_orders"

    assert "direct_upstream" in result

    assert "upstream_ancestors" in result

    assert "direct_downstream" in result

    assert "downstream_blast_radius" in result


# ============================================================
# TEST 4 — SQL HEALING
# ============================================================

def test_sql_healing():
    """Verify SQL healer processes the SQL file."""

    from src.agent.nodes.sql_healer import heal_sql

    result = heal_sql(
        sql_file=str(SQL_FILE),
        input_file=str(INPUT_FILE),
    )

    assert isinstance(result, dict)

    assert result["success"] is True

    assert "original_sql" in result

    assert "repaired_sql" in result

    assert "sql_changed" in result


# ============================================================
# TEST 5 — REMEDIATION
# ============================================================

def test_remediation():
    """Verify remediation processes DQ issues."""

    from src.agent.nodes.dq_detect import detect_dq_issues
    from src.agent.nodes.remediation import remediate_dq_issues

    dq_result = detect_dq_issues(
        str(INPUT_FILE)
    )

    result = remediate_dq_issues(
        input_file=str(INPUT_FILE),
        issues=dq_result["issues"],
    )

    assert isinstance(result, dict)

    assert result["total_rows"] == 500

    assert result["issues_received"] == dq_result["issue_count"]

    assert "actions" in result

    assert "quarantined_rows" in result


# ============================================================
# TEST 6 — GUARDRAILS
# ============================================================

def test_guardrails():
    """Verify HIGH severity issues trigger controlled remediation."""

    from src.agent.nodes.dq_detect import detect_dq_issues
    from src.agent.nodes.guardrails import apply_guardrails

    dq_result = detect_dq_issues(
        str(INPUT_FILE)
    )

    result = apply_guardrails(
        dq_result
    )

    assert isinstance(result, dict)

    assert result["approved"] is True

    assert result["action"] == "CONTROLLED_REMEDIATION"

    assert result["errors"] == []


# ============================================================
# TEST 7 — COMPLETE PIPELINE
# ============================================================

def test_complete_pipeline():
    """Verify the complete ObsidianDQ pipeline executes."""

    from src.agent.graph import run_pipeline

    result = run_pipeline(
        input_file=str(INPUT_FILE),
        sql_file=str(SQL_FILE),
    )

    assert isinstance(result, dict)

    assert result["pipeline_name"] == "ObsidianDQ"

    assert result["affected_stage"] == "stg_orders"

    assert result["issue_count"] >= 1

    assert result["requires_human_approval"] is True

    assert result["pipeline_status"] == "WAITING_FOR_HUMAN_APPROVAL"

    assert result["route_taken"] == ["needs_human_review"]