import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from backend.main import app


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_run_and_approval_return_dashboard_contract(monkeypatch):
    """The UI receives the same normalized payload before and after approval."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    client = TestClient(app)
    run = client.post("/api/pipeline/run", json={
        "input_file": str(PROJECT_ROOT / "data" / "raw" / "stg_orders.parquet"),
        "sql_file": str(PROJECT_ROOT / "data" / "queries" / "fct_sales.sql"),
        "lineage_file": str(PROJECT_ROOT / "data" / "lineage" / "lineage.json"),
    })
    assert run.status_code == 200
    payload = run.json()
    assert payload["requires_human_approval"] is True
    assert payload["data_snapshot"]["row_count"] == 500
    assert payload["issues"]

    proposal = payload["root_cause_analysis"]["agent_proposed_actions"][0]
    approved = client.post("/api/pipeline/approve", json={
        "run_id": payload["run_id"],
        "issue_id": proposal["issue_id"],
        "decision": "approve",
    })
    assert approved.status_code == 200
    resumed = approved.json()
    assert resumed["workflow_status"] == "APPROVED"
    assert resumed["guardrails"]["approved"] is True
    assert "data_snapshot" in resumed


def test_upload_rejects_unsupported_file_type():
    response = TestClient(app).post(
        "/api/pipeline/upload",
        data={"file_type": "dataset"},
        files={"file": ("notes.txt", b"not a dataset", "text/plain")},
    )
    assert response.status_code == 400
    assert "Unsupported dataset" in response.json()["detail"]


def test_sql_and_lineage_uploads_use_their_multipart_file_type():
    client = TestClient(app)
    sql = client.post(
        "/api/pipeline/upload",
        data={"file_type": "sql"},
        files={"file": ("transform.sql", b"SELECT 1;", "text/plain")},
    )
    assert sql.status_code == 200
    assert sql.json()["file_type"] == "sql"
    assert sql.json()["preview"]["parsed"] is True

    lineage = client.post(
        "/api/pipeline/upload",
        data={"file_type": "lineage"},
        files={"file": ("lineage.json", b'{"nodes": [], "edges": []}', "application/json")},
    )
    assert lineage.status_code == 200
    assert lineage.json()["file_type"] == "lineage"
    assert lineage.json()["preview"] == {"node_count": 0, "edge_count": 0}
