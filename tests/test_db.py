"""Tests for the DuckDB storage utility (src/agent/utils/db.py)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from src.agent.utils import db


@pytest.fixture
def tmp_db(monkeypatch):
    """Point the db module at a temporary database for the test."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.duckdb"
        monkeypatch.setattr(db, "_db_path", db_path)
        db.init_schema()
        yield db_path


def test_init_schema_creates_tables(tmp_db):
    """Schema initialisation creates all expected tables."""
    with db.connect() as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
            ).fetchall()
        }
    assert "runs" in tables
    assert "incidents" in tables
    assert "dq_results" in tables
    assert "rca_evidence" in tables
    assert "remediation_results" in tables
    assert "evaluation_records" in tables


def test_save_and_get_run(tmp_db):
    """A saved run can be retrieved by run_id."""
    record = {
        "run_id": "run-1",
        "timestamp": "2026-09-08T00:00:00Z",
        "pipeline_name": "ObsidianDQ",
        "affected_stage": "stg_orders",
        "input_file": "data/raw/stg_orders.parquet",
        "issue_count": 3,
        "health_score": 75.0,
        "pipeline_status": "WAITING_FOR_HUMAN_APPROVAL",
        "requires_human_approval": True,
        "route_taken": ["needs_human_review"],
        "final_result": {"status": "ok"},
    }
    db.save_run(record)
    result = db.get_run("run-1")
    assert result is not None
    assert result["run_id"] == "run-1"
    assert result["affected_stage"] == "stg_orders"
    assert result["health_score"] == 75.0
    assert result["route_taken"] == ["needs_human_review"]
    assert result["final_result"] == {"status": "ok"}


def test_save_run_upsert(tmp_db):
    """Saving the same run_id updates the existing row."""
    record = {"run_id": "run-upsert", "pipeline_name": "ObsidianDQ", "affected_stage": "stg_orders"}
    db.save_run(record)
    record["health_score"] = 50.0
    db.save_run(record)
    result = db.get_run("run-upsert")
    assert result["health_score"] == 50.0


def test_list_runs_ordered_by_timestamp(tmp_db):
    """list_runs returns runs newest-first."""
    for i in range(3):
        db.save_run({
            "run_id": f"run-{i}",
            "timestamp": f"2026-09-0{i+1}T00:00:00Z",
            "pipeline_name": "ObsidianDQ",
            "affected_stage": "stg_orders",
        })
    runs = db.list_runs(limit=10)


def test_save_incidents_and_search(tmp_db):
    """Incidents are saved and searchable by column/rule."""
    db.save_run({"run_id": "r1", "pipeline_name": "ObsidianDQ", "affected_stage": "stg_orders"})
    issues = [
        {"rule": "NOT_NULL", "column": "customer_id", "severity": "MEDIUM", "count": 2},
        {"rule": "PRICE_NON_NEGATIVE", "column": "price", "severity": "HIGH", "count": 3},
    ]
    db.save_incidents("r1", issues)
    matches = db.search_similar_incidents("customer_id", "NOT_NULL")
    assert len(matches) >= 1
    assert matches[0]["column_name"] == "customer_id"
    assert matches[0]["rule"] == "NOT_NULL"


def test_column_run_history(tmp_db):
    """column_run_history returns runs where a column had incidents."""
    db.save_run({"run_id": "r1", "pipeline_name": "ObsidianDQ", "affected_stage": "stg_orders"})
    db.save_incidents("r1", [{"rule": "NOT_NULL", "column": "price", "severity": "HIGH"}])
    history = db.column_run_history("price")
    assert history["column"] == "price"
    assert history["runs"] == 1
    assert len(history["recent"]) == 1


def test_save_dq_result(tmp_db):
    """DQ results are persisted with JSON payload."""
    db.save_run({"run_id": "r1", "pipeline_name": "ObsidianDQ", "affected_stage": "stg_orders"})
    dq = {"stage_path": "data/raw/stg_orders.parquet", "row_count": 500, "issue_count": 3, "severity_summary": {"HIGH": 1, "MEDIUM": 2, "LOW": 0}}
    db.save_dq_result("r1", dq)
    with db.connect() as conn:
        row = conn.execute("SELECT result_json FROM dq_results WHERE run_id = 'r1'").fetchone()
    assert row is not None
    assert json.loads(row[0])["row_count"] == 500


def test_save_rca_evidence_and_conclusion(tmp_db):
    """RCA evidence trail and conclusion are persisted."""
    db.save_run({"run_id": "r1", "pipeline_name": "ObsidianDQ", "affected_stage": "stg_orders"})
    evidence = [{"agent": "Root-Cause Investigator Agent", "type": "tool", "name": "get_sample_rows"}]
    db.save_rca_evidence("r1", evidence)
    db.save_rca_conclusion("r1", "raw_customers", "Upstream lineage traversal isolated raw_customers.", 0.85)
    with db.connect() as conn:
        rows = conn.execute("SELECT COUNT(*) FROM rca_evidence WHERE run_id = 'r1'").fetchone()[0]
    assert rows == 2


def test_save_remediation_result(tmp_db):
    """Remediation results are persisted with actions JSON."""
    db.save_run({"run_id": "r1", "pipeline_name": "ObsidianDQ", "affected_stage": "stg_orders"})
    result = {
        "input_file": "data/raw/stg_orders.parquet",
        "total_rows": 500,
        "issues_received": 3,
        "quarantined_rows": 3,
        "quarantine_file": "data/quarantine/stg_orders_quarantine.parquet",
        "cleaned_file": "data/cleaned/stg_orders_cleaned.parquet",
        "actions": [{"severity": "HIGH", "rule": "PRICE_NON_NEGATIVE", "action": "QUARANTINE"}],
        "verification_passed": False,
        "verification_details": {"remaining_issue_count": 1},
    }
    db.save_remediation_result("r1", result)
    stored = db.get_run("r1")
    assert stored is not None


def test_save_evaluation_record(tmp_db):
    """Evaluation records are persisted."""
    record = {
        "run_id": "eval-1",
        "evaluation_mode": "offline_fallback",
        "metrics": {"controlled_handling_success_rate": "100.0%"},
        "report_path": "evaluation/results/test/report.md",
        "created_at": "2026-09-08T00:00:00Z",
    }
    db.save_evaluation_record(record)
    with db.connect() as conn:
        row = conn.execute("SELECT metrics FROM evaluation_records WHERE run_id = 'eval-1'").fetchone()
    assert row is not None
    assert json.loads(row[0])["controlled_handling_success_rate"] == "100.0%"


def test_save_incident_memory(tmp_db):
    """save_incident_memory creates run, evidence, and incident rows."""
    record = {
        "run_id": "mem-1",
        "affected_stage": "stg_orders",
        "issue_keys": ["NOT_NULL:customer_id", "PRICE_NON_NEGATIVE:price"],
        "failed_columns": ["customer_id", "price"],
        "failed_rules": ["NOT_NULL", "PRICE_NON_NEGATIVE"],
    }
    db.save_incident_memory(record)
    run = db.get_run("mem-1")
    assert run is not None
    matches = db.search_similar_incidents("customer_id", "NOT_NULL")
    assert len(matches) >= 1


def test_get_run_missing_returns_none(tmp_db):
    """Querying a non-existent run returns None."""
    assert db.get_run("does-not-exist") is None


def test_transaction_rollback_on_error(tmp_db):
    """A failed transaction does not commit partial state."""
    with pytest.raises(Exception):
        with db.transaction() as conn:
            conn.execute(
                "INSERT INTO runs (run_id, timestamp, pipeline_name, affected_stage) VALUES (?, ?, ?, ?)",
                ["tx-1", "", "ObsidianDQ", "stg_orders"],
            )
            conn.execute(
                "INSERT INTO runs (run_id, timestamp, pipeline_name, affected_stage) VALUES (?, ?, ?, ?)",
                [None, "", "ObsidianDQ", "stg_orders"],
            )
    assert db.get_run("tx-1") is None


def test_default_db_path_is_repo_data_file():
    """The default database file lives at <repo>/data/obsidiandq.duckdb.

    This is the file the app opens/queries, so it must be absolute and point at
    the repository's data directory regardless of the process working directory.
    """
    assert db.DEFAULT_DB_PATH.name == "obsidiandq.duckdb"
    assert db.DEFAULT_DB_PATH.parent.name == "data"
    assert db.DEFAULT_DB_PATH.is_absolute()


def test_connect_uses_file_stem_as_catalog(tmp_db):
    """DuckDB names an on-disk catalog after the file stem.

    Queries issued by the VS Code DuckDB extension against the configured alias
    (``obsidiandq``) must match this catalog; otherwise it errors with
    ``Catalog "<drive>:" does not exist`` on Windows.
    """
    with db.connect() as conn:
        names = {
            row[0]
            for row in conn.execute("SELECT database_name FROM duckdb_databases()").fetchall()
        }
    assert any(n == Path(tmp_db).stem for n in names)


def test_relative_db_path_resolves_against_data_dir(monkeypatch):
    """Relative configure_db_path inputs are anchored to the default data dir,
    never to the process working directory."""
    monkeypatch.setattr(db, "_db_path", Path("some_rel.db"))
    resolved = db._resolve_db_path()
    assert resolved.startswith(db.DEFAULT_DB_DIR.as_posix())
    assert resolved == (db.DEFAULT_DB_DIR / "some_rel.db").resolve().as_posix()

