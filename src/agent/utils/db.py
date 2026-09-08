"""DuckDB-backed persistent storage for ObsidianDQ structured records.

Replaces the JSONL-based run history and incident memory with a single
local DuckDB database. CSV/Parquet files remain the input/output dataset
format; this module stores only structured metadata and results.

Tables
------
runs                - one row per pipeline execution
incidents           - individual DQ issues linked to a run
dq_results          - full DQ detection result payloads
rca_evidence        - root-cause investigation evidence trails
remediation_results - remediation actions and outcomes
evaluation_records  - controlled-benchmark evaluation payloads

Connection strategy
--------------------
DuckDB only allows a single read-write connection to a given database
file at a time. The original implementation opened and closed a brand
new connection on every call, which meant any other process touching
the file for even a moment (e.g. a VS Code DuckDB Table Viewer tab)
would cause a hard failure on startup or mid-request.

This module instead holds ONE persistent connection for the lifetime of
the process (see ``_get_shared_connection`` / ``close_connection``), so
the file lock is acquired once at startup and released once at shutdown.
"""

from __future__ import annotations

import atexit
import json
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Optional

import duckdb

DEFAULT_DB_PATH = Path(__file__).resolve().parents[3] / "data" / "obsidiandq.duckdb"
# Default parent directory used to anchor relative paths supplied to
# ``configure_db_path`` so the target file is unambiguous regardless of the
# process current working directory.
DEFAULT_DB_DIR = DEFAULT_DB_PATH.parent

_db_path: Path = DEFAULT_DB_PATH
_path_lock = threading.Lock()

# --- Shared connection state -------------------------------------------------
_conn: Optional[duckdb.DuckDBPyConnection] = None
_conn_lock = threading.Lock()


def configure_db_path(path: str | Path) -> None:
    """Set the database path.

    If a connection is already open (e.g. because the module-level
    ``init_schema()`` ran against the default path on import), it is
    closed first so the next call transparently reopens against the new
    path. Safe to call at any time.
    """
    global _db_path
    with _path_lock:
        _db_path = Path(path)
    close_connection()


def get_db_path() -> Path:
    return _db_path


def _resolve_db_path() -> str:
    """Return an absolute, normalized path to the DuckDB database file.

    Relative paths are anchored to ``data/`` (the default database directory)
    rather than the process working directory, and a trailing ``.duckdb``
    extension is applied when omitted. The final path always uses forward
    slashes, which keeps Windows drive-letter paths unambiguous for DuckDB.
    """
    path = _db_path
    if not path.is_absolute():
        path = DEFAULT_DB_DIR / path
    if path.suffix.lower() != ".duckdb" and path.suffix == "":
        path = path.with_suffix(".duckdb")
    return path.resolve().as_posix()


def _open_with_retry(
    db_path: str, retries: int = 5, delay: float = 0.5
) -> duckdb.DuckDBPyConnection:
    """Open a DuckDB connection, retrying briefly if the file is locked.

    This absorbs transient lock contention at startup (e.g. a VS Code
    DuckDB viewer tab that happens to be attached at the moment the app
    boots) instead of crashing immediately.
    """
    last_err: Optional[Exception] = None
    for attempt in range(retries):
        try:
            return duckdb.connect(db_path)
        except duckdb.IOException as e:
            last_err = e
            if attempt < retries - 1:
                time.sleep(delay)
    assert last_err is not None
    raise last_err


def _get_shared_connection() -> duckdb.DuckDBPyConnection:
    """Return the single persistent DuckDB connection, opening it on first use."""
    global _conn
    if _conn is None:
        with _conn_lock:
            if _conn is None:  # re-check inside the lock (double-checked locking)
                db_path = _resolve_db_path()
                Path(db_path).parent.mkdir(parents=True, exist_ok=True)
                _conn = _open_with_retry(db_path)
    return _conn


def close_connection() -> None:
    """Close the shared connection, if open.

    Call this from your app's shutdown hook (e.g. FastAPI's
    ``@app.on_event("shutdown")`` or a lifespan context manager) so the
    file lock is released cleanly. Also registered via ``atexit`` as a
    fallback for interpreter exit / Ctrl+C.
    """
    global _conn
    with _conn_lock:
        if _conn is not None:
            _conn.close()
            _conn = None


atexit.register(close_connection)


@contextmanager
def connect() -> Iterator[duckdb.DuckDBPyConnection]:
    """Yield the shared DuckDB connection.

    This does NOT open/close a new connection per call — see the module
    docstring for why that matters. The connection stays open for the
    life of the process; call ``close_connection()`` on shutdown.
    """
    conn = _get_shared_connection()
    yield conn


@contextmanager
def transaction() -> Iterator[duckdb.DuckDBPyConnection]:
    """Yield the shared connection with auto-commit on success, rollback on error."""
    with connect() as conn:
        conn.begin()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise


_SCHEMA_STATEMENTS = [
    """
    CREATE SEQUENCE IF NOT EXISTS runs_seq START 1;
    CREATE TABLE IF NOT EXISTS runs (
        run_id          TEXT PRIMARY KEY,
        timestamp       TEXT NOT NULL,
        pipeline_name   TEXT NOT NULL,
        affected_stage  TEXT NOT NULL,
        input_file      TEXT,
        sql_file        TEXT,
        lineage_file    TEXT,
        row_count       INTEGER,
        column_count    INTEGER,
        issue_count     INTEGER DEFAULT 0,
        health_score    REAL,
        pipeline_status TEXT,
        requires_human_approval BOOLEAN DEFAULT FALSE,
        route_taken     JSON,
        final_result    JSON
    );
    """,
    """
    CREATE SEQUENCE IF NOT EXISTS incidents_seq START 1;
    CREATE TABLE IF NOT EXISTS incidents (
        id              INTEGER PRIMARY KEY DEFAULT nextval('incidents_seq'),
        run_id          TEXT NOT NULL,
        rule            TEXT,
        column_name     TEXT,
        severity        TEXT,
        description     TEXT,
        issue_count     INTEGER,
        issue_key       TEXT,
        FOREIGN KEY (run_id) REFERENCES runs(run_id)
    );
    """,
    """
    CREATE SEQUENCE IF NOT EXISTS dq_results_seq START 1;
    CREATE TABLE IF NOT EXISTS dq_results (
        id              INTEGER PRIMARY KEY DEFAULT nextval('dq_results_seq'),
        run_id          TEXT NOT NULL,
        stage_path      TEXT,
        row_count       INTEGER,
        issue_count     INTEGER,
        severity_summary JSON,
        result_json     JSON,
        FOREIGN KEY (run_id) REFERENCES runs(run_id)
    );
    """,
    """
    CREATE SEQUENCE IF NOT EXISTS rca_evidence_seq START 1;
    CREATE TABLE IF NOT EXISTS rca_evidence (
        id              INTEGER PRIMARY KEY DEFAULT nextval('rca_evidence_seq'),
        run_id          TEXT NOT NULL,
        agent           TEXT,
        evidence_type   TEXT,
        evidence_json   TEXT,
        root_cause_stage TEXT,
        root_cause_reasoning TEXT,
        confidence_score REAL,
        FOREIGN KEY (run_id) REFERENCES runs(run_id)
    );
    """,
    """
    CREATE SEQUENCE IF NOT EXISTS remediation_results_seq START 1;
    CREATE TABLE IF NOT EXISTS remediation_results (
        id              INTEGER PRIMARY KEY DEFAULT nextval('remediation_results_seq'),
        run_id          TEXT NOT NULL,
        input_file      TEXT,
        total_rows      INTEGER,
        issues_received INTEGER,
        quarantined_rows INTEGER,
        quarantine_file TEXT,
        cleaned_file    TEXT,
        actions         JSON,
        verification_passed BOOLEAN,
        verification_details JSON,
        FOREIGN KEY (run_id) REFERENCES runs(run_id)
    );
    """,
    """
    CREATE SEQUENCE IF NOT EXISTS evaluation_records_seq START 1;
    CREATE TABLE IF NOT EXISTS evaluation_records (
        id              INTEGER PRIMARY KEY DEFAULT nextval('evaluation_records_seq'),
        run_id          TEXT,
        evaluation_mode TEXT,
        metrics         JSON,
        report_path     TEXT,
        created_at      TEXT
    );
    """,
]


def init_schema(conn: Optional[duckdb.DuckDBPyConnection] = None) -> None:
    if conn is not None:
        for statement in _SCHEMA_STATEMENTS:
            conn.execute(statement)
        return

    with connect() as conn:
        for statement in _SCHEMA_STATEMENTS:
            conn.execute(statement)


def save_run(record: dict[str, Any]) -> None:
    with transaction() as conn:
        conn.execute(
            """
            INSERT INTO runs (
                run_id, timestamp, pipeline_name, affected_stage,
                input_file, sql_file, lineage_file,
                row_count, column_count, issue_count, health_score,
                pipeline_status, requires_human_approval, route_taken, final_result
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (run_id) DO UPDATE SET
                pipeline_status = excluded.pipeline_status,
                health_score = excluded.health_score,
                route_taken = excluded.route_taken,
                final_result = excluded.final_result
            """,
            [
                record["run_id"],
                record.get("timestamp", ""),
                record.get("pipeline_name", ""),
                record.get("affected_stage", ""),
                record.get("input_file"),
                record.get("sql_file"),
                record.get("lineage_file"),
                record.get("row_count"),
                record.get("column_count"),
                record.get("issue_count", 0),
                record.get("health_score"),
                record.get("pipeline_status"),
                record.get("requires_human_approval", False),
                json.dumps(record.get("route_taken", []), default=str),
                json.dumps(record.get("final_result", {}), default=str),
            ],
        )


def get_run(run_id: str) -> Optional[dict[str, Any]]:
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM runs WHERE run_id = ?", [run_id]
        ).fetchone()
        if row is None:
            return None
        columns = [desc[0] for desc in conn.description]
        return _deserialize_run(dict(zip(columns, row)))


def list_runs(limit: int = 50) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM runs ORDER BY timestamp DESC LIMIT ?", [limit]
        ).fetchall()
        columns = [desc[0] for desc in conn.description]
        return [_deserialize_run(dict(zip(columns, row))) for row in rows]


def _deserialize_run(row: dict[str, Any]) -> dict[str, Any]:
    for key in ("route_taken", "final_result"):
        value = row.get(key)
        if isinstance(value, str):
            try:
                row[key] = json.loads(value)
            except json.JSONDecodeError:
                row[key] = None
    return row


def save_incidents(run_id: str, issues: list[dict[str, Any]]) -> None:
    if not issues:
        return
    with transaction() as conn:
        conn.executemany(
            """
            INSERT INTO incidents (
                run_id, rule, column_name, severity, description,
                issue_count, issue_key
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    run_id,
                    issue.get("rule"),
                    issue.get("column"),
                    issue.get("severity"),
                    issue.get("description") or issue.get("issue"),
                    issue.get("count"),
                    f"{issue.get('rule', '')}:{issue.get('column', '')}",
                )
                for issue in issues
            ],
        )


def search_similar_incidents(column: str, rule: str, limit: int = 5) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT i.*, r.timestamp
            FROM incidents i
            JOIN runs r ON r.run_id = i.run_id
            WHERE i.issue_key = ?
               OR (i.column_name = ? AND i.rule = ?)
            ORDER BY r.timestamp DESC
            LIMIT ?
            """,
            [f"{rule}:{column}", column, rule, limit],
        ).fetchall()
        columns = [desc[0] for desc in conn.description]
        return [dict(zip(columns, row)) for row in rows]


def column_run_history(column: str, limit: int = 5) -> dict[str, Any]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT r.run_id, r.timestamp, r.affected_stage, r.health_score,
                   r.issue_count, r.pipeline_status
            FROM runs r
            JOIN incidents i ON i.run_id = r.run_id
            WHERE i.column_name = ?
            ORDER BY r.timestamp DESC
            LIMIT ?
            """,
            [column, limit],
        ).fetchall()
        columns = [desc[0] for desc in conn.description]
        matches = [dict(zip(columns, row)) for row in rows]
        return {"column": column, "runs": len(matches), "recent": matches}


def save_dq_result(run_id: str, result: dict[str, Any]) -> None:
    with transaction() as conn:
        conn.execute(
            """
            INSERT INTO dq_results (
                run_id, stage_path, row_count, issue_count,
                severity_summary, result_json
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                run_id,
                result.get("stage_path"),
                result.get("row_count"),
                result.get("issue_count"),
                json.dumps(result.get("severity_summary", {}), default=str),
                json.dumps(result, default=str),
            ],
        )


def save_rca_evidence(run_id: str, evidence: list[dict[str, Any]]) -> None:
    if not evidence:
        return
    with transaction() as conn:
        conn.executemany(
            """
            INSERT INTO rca_evidence (
                run_id, agent, evidence_type, evidence_json
            ) VALUES (?, ?, ?, ?)
            """,
            [
                (
                    run_id,
                    item.get("agent"),
                    item.get("type"),
                    json.dumps(item, default=str),
                )
                for item in evidence
            ],
        )


def save_rca_conclusion(
    run_id: str,
    root_cause_stage: str,
    root_cause_reasoning: str,
    confidence_score: float,
) -> None:
    with transaction() as conn:
        conn.execute(
            """
            INSERT INTO rca_evidence (
                run_id, agent, evidence_type, evidence_json,
                root_cause_stage, root_cause_reasoning, confidence_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                run_id,
                "root_cause_conclusion",
                "conclusion",
                json.dumps(
                    {
                        "root_cause_stage": root_cause_stage,
                        "root_cause_reasoning": root_cause_reasoning,
                        "confidence_score": confidence_score,
                    },
                    default=str,
                ),
                root_cause_stage,
                root_cause_reasoning,
                confidence_score,
            ],
        )


def save_remediation_result(run_id: str, result: dict[str, Any]) -> None:
    with transaction() as conn:
        conn.execute(
            """
            INSERT INTO remediation_results (
                run_id, input_file, total_rows, issues_received,
                quarantined_rows, quarantine_file, cleaned_file,
                actions, verification_passed, verification_details
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                run_id,
                result.get("input_file"),
                result.get("total_rows"),
                result.get("issues_received"),
                result.get("quarantined_rows"),
                result.get("quarantine_file"),
                result.get("cleaned_file"),
                json.dumps(result.get("actions", []), default=str),
                result.get("verification_passed"),
                json.dumps(result.get("verification_details", {}), default=str),
            ],
        )


def save_evaluation_record(record: dict[str, Any]) -> None:
    with transaction() as conn:
        conn.execute(
            """
            INSERT INTO evaluation_records (
                run_id, evaluation_mode, metrics, report_path, created_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            [
                record.get("run_id"),
                record.get("evaluation_mode"),
                json.dumps(record.get("metrics", {}), default=str),
                record.get("report_path"),
                record.get("created_at"),
            ],
        )


def save_incident_memory(record: dict[str, Any]) -> None:
    run_id = record.get("run_id", "")
    with transaction() as conn:
        conn.execute(
            """
            INSERT INTO runs (run_id, timestamp, pipeline_name, affected_stage)
            VALUES (?, ?, 'ObsidianDQ', ?)
            ON CONFLICT (run_id) DO NOTHING
            """,
            [run_id, record.get("timestamp", ""), record.get("affected_stage", "")],
        )
        conn.execute(
            """
            INSERT INTO rca_evidence (run_id, agent, evidence_type, evidence_json)
            VALUES (?, ?, 'incident_memory', ?)
            """,
            [run_id, record.get("agent", "incident_memory"), json.dumps(record, default=str)],
        )
        for key in record.get("issue_keys", []):
            if ":" in key:
                rule, column = key.split(":", 1)
            else:
                rule, column = key, None
            conn.execute(
                """
                INSERT INTO incidents (
                    run_id, rule, column_name, severity, description, issue_key
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                [run_id, rule, column, record.get("severity"), record.get("description"), key],
            )


init_schema()