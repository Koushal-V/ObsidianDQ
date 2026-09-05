import json
import os
import sys
import time
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd

# Load environment variables from .env
load_dotenv()

# Ensure project root is in python path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agent.graph import build_graph, run_pipeline
from src.agent.nodes.stage_profile import profile_stage
from src.agent.nodes.remediation import remediate_dq_issues
from src.agent.nodes.guardrails import apply_guardrails
from src.agent.utils.llm import generate_text, get_llm_provider

app = FastAPI(title="ObsidianDQ Backend API", version="2.0.0")
RUN_STATES: Dict[str, Dict[str, Any]] = {}


def generate_gemini_summary(affected_stage: str, issue_count: int, issues: list, upstream_path: list) -> str:
    """
    Generate natural-language summary explanation using Gemini API if key is present.
    """
    default_summary = (
        f"Anomalies detected in '{affected_stage}': {issue_count} issue(s) found including nulls, negative prices, or invalid values."
        if issue_count > 0
        else "No anomalies detected. Data pipeline is operating nominally."
    )

    if not get_llm_provider():
        return default_summary

    try:
        prompt = f"""
        You are an expert Data Observability AI. Write a concise 2-sentence executive root cause summary for a data quality failure in an enterprise ETL pipeline:
        - Affected Stage/Table: {affected_stage}
        - Total Issues Count: {issue_count}
        - Detailed Issue List: {issues}
        - Upstream Dependency Chain: {" -> ".join(upstream_path)}

        Keep the narrative technical, precise, and actionable for a senior data engineer.
        """
        response = generate_text(prompt)
        if response:
            return response
    except Exception as exc:
        print(f"[Gemini LLM Summary Warning] {exc}")

    return default_summary


def _log_run_history(response_data: dict):
    """
    Persist pipeline run summary to data/run_history.jsonl.
    """
    try:
        history_file = PROJECT_ROOT / "data" / "run_history.jsonl"
        history_file.parent.mkdir(parents=True, exist_ok=True)
        failed_columns = list({
            iss.get("column")
            for iss in response_data.get("issues", [])
            if iss.get("column")
        })
        record = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "run_id": response_data.get("run_id", ""),
            "affected_stage": response_data.get("root_cause_analysis", {}).get("failing_table", "stg_orders"),
            "health_score": response_data.get("pipeline_health", {}).get("overall_health_score", 100),
            "failed_columns": failed_columns,
            "issue_count": len(response_data.get("issues", [])),
        }
        with history_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except Exception as exc:
        print(f"[Run History Logging Warning] {exc}")


# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = PROJECT_ROOT / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class PipelineRunRequest(BaseModel):
    input_file: Optional[str] = None
    sql_file: Optional[str] = None
    lineage_file: Optional[str] = None


class QuarantineRequest(BaseModel):
    input_file: Optional[str] = None
    quarantine_sql: Optional[str] = None


class ApprovalRequest(BaseModel):
    run_id: str
    issue_id: str
    decision: str
    action: Optional[str] = None


def format_3tier_response(state: Dict[str, Any], duration_ms: int) -> Dict[str, Any]:
    """
    Format raw LangGraph AgentState into the requested 3-Tier JSON schema.
    """
    issues = state.get("issues", [])
    issue_count = state.get("issue_count", len(issues))
    severity_summary = state.get("severity_summary", {"HIGH": 0, "MEDIUM": 0, "LOW": 0})
    
    # ----------------------------------------------------
    # TIER 1: Pipeline Health Telemetry
    # ----------------------------------------------------
    high_sev = severity_summary.get("HIGH", 0)
    med_sev = severity_summary.get("MEDIUM", 0)
    high_issue_stages = {
        state.get("affected_stage")
        for issue in issues
        if str(issue.get("severity", "")).upper() == "HIGH"
    }
    
    if high_sev > 0 or issue_count > 3:
        status = "ANOMALIES_DETECTED"
    elif med_sev > 0 or issue_count > 0:
        status = "WARNING"
    else:
        status = "HEALTHY"

    # Health score formula (100 base - 15*HIGH - 5*MED - 2*LOW)
    raw_score = 100 - (high_sev * 15 + med_sev * 5 + severity_summary.get("LOW", 0) * 2)
    overall_health_score = max(0, min(100, raw_score))
    
    row_count = state.get("row_count", 0)
    
    scanned_tables = ["raw_customers", "stg_orders", "fct_sales"]
    if state.get("lineage") and isinstance(state["lineage"], dict):
        nodes = state["lineage"].get("nodes", [])
        if nodes:
            scanned_tables = [n.get("name", str(n)) for n in nodes if isinstance(n, (dict, str))]
    
    pipeline_health = {
        "status": status,
        "overall_health_score": overall_health_score,
        "total_records_scanned": row_count if row_count > 0 else 500,
        "execution_duration_ms": duration_ms,
        "scanned_tables": list(dict.fromkeys(scanned_tables)),
    }

    # ----------------------------------------------------
    # TIER 2A: Lineage Graph (@xyflow/react format)
    # ----------------------------------------------------
    lineage_file = state.get("lineage_file", "data/lineage/lineage.json")
    lineage_path = Path(lineage_file)
    if not lineage_path.is_absolute():
        lineage_path = PROJECT_ROOT / lineage_path
    
    lineage_data = {}
    if lineage_path.exists():
        try:
            lineage_data = json.loads(lineage_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    nodes = []
    edges = []

    raw_nodes = lineage_data.get("nodes", [
        {"name": "raw_customers", "type": "CSV"},
        {"name": "stg_orders", "type": "Parquet"},
        {"name": "fct_sales", "type": "SQL View"}
    ])

    affected_stage = state.get("affected_stage", "stg_orders")

    for node in raw_nodes:
        if isinstance(node, dict):
            n_id = node.get("name") or node.get("id", "node")
            n_type = node.get("type", "Dataset")
        else:
            n_id = str(node)
            n_type = "Dataset"
            
        label = f"{n_id} ({n_type})"
        
        if n_id == affected_stage and n_id in high_issue_stages:
            n_status = "FAILED"
        elif n_id == affected_stage and issue_count > 0:
            n_status = "ATTENTION"
        elif n_id == "fct_sales":
            n_status = "DEGRADED" if issue_count > 0 else "HEALTHY"
        else:
            n_status = "HEALTHY"

        nodes.append({
            "id": n_id,
            "label": label,
            "status": n_status,
        })

    raw_edges = lineage_data.get("edges", [
        {"source": "raw_customers", "target": "stg_orders"},
        {"source": "stg_orders", "target": "fct_sales"},
        {"source": "raw_customers", "target": "fct_sales"}
    ])

    for edge in raw_edges:
        if isinstance(edge, dict):
            src = edge.get("source") or edge.get("from")
            tgt = edge.get("target") or edge.get("to")
            if src and tgt:
                edges.append({"source": str(src), "target": str(tgt)})

    lineage_graph = {
        "nodes": nodes,
        "edges": edges,
    }

    # ----------------------------------------------------
    # TIER 2B: SQL Diagnostics
    # ----------------------------------------------------
    orig_sql = state.get("original_sql", "")
    repaired_sql = state.get("repaired_sql", "")
    sql_changed = state.get("sql_changed", False)
    sql_healing_ran = bool(state.get("sql_validation"))
    has_real_sql_repair = any(
        isinstance(repair, dict) and repair.get("type") == "COLUMN_REPAIR"
        for repair in state.get("sql_repairs", [])
    )
    
    tokens_replaced = []
    for repair in state.get("sql_repairs", []):
        if isinstance(repair, dict):
            tokens_replaced.append({
                "original_token": repair.get("old", "AST Clause"),
                "corrected_token": repair.get("new", "AST Normalized"),
                "reason": repair.get("description", "AST token matching against DuckDB schema.")
            })
    
    sql_diagnostics = {
        "sql_healing_ran": sql_healing_ran,
        "has_error": len(state.get("sql_problems", [])) > 0 or has_real_sql_repair,
        "original_sql": orig_sql,
        "repaired_sql": repaired_sql,
        "tokens_replaced": tokens_replaced
    }

    # ----------------------------------------------------
    # TIER 2C: Root Cause & Auto-Quarantine Analysis
    # ----------------------------------------------------
    blast_radius_count = state.get("blast_radius_count", len(state.get("downstream_blast_radius", [])))
    blast_radius_text = f"{blast_radius_count + 1} downstream dashboard{'s' if blast_radius_count != 0 else ''} affected"
    
    upstream_path = list(reversed(state.get("upstream_ancestors", [])))
    if affected_stage not in upstream_path:
        upstream_path.append(affected_stage)
    if not upstream_path:
        upstream_path = [affected_stage]
    summary_explanation = generate_gemini_summary(
        affected_stage=affected_stage,
        issue_count=issue_count,
        issues=issues,
        upstream_path=upstream_path
    )

    predicates = []
    for issue in issues:
        rule = issue.get("rule")
        column = issue.get("column")
        if rule == "NOT_NULL" and column:
            predicates.append(f"{column} IS NULL")
        elif rule == "PRICE_NON_NEGATIVE" and column:
            predicates.append(f"{column} < 0")
        elif rule == "VALID_STATUS" and column:
            predicates.append(f"{column} NOT IN ('COMPLETED', 'PENDING', 'CANCELLED')")
    quarantine_sql = (
        f"CREATE TABLE {affected_stage}_quarantine AS SELECT * FROM {affected_stage} WHERE {' OR '.join(predicates)};"
        if predicates
        else f"CREATE TABLE {affected_stage}_quarantine AS SELECT * FROM {affected_stage} WHERE 1 = 0;"
    )

    agent_reasoning = []
    for step in state.get("agent_reasoning", []):
        if step.get("type") == "warning":
            agent_reasoning.append({
                "type": "warning",
                "text": "AI analysis unavailable - using safe default.",
                "debug_detail": step.get("text", ""),
            })
        else:
            agent_reasoning.append(step)

    root_cause_analysis = {
        "failing_table": state.get("affected_stage", "fct_sales"),
        "root_cause_table": state.get("root_cause_stage", "stg_orders"),
        "upstream_path": upstream_path,
        "summary_explanation": summary_explanation,
        "severity_score": min(10, max(1, high_sev * 3 + med_sev * 2 + 1)),
        "blast_radius": blast_radius_text,
        "auto_quarantine_sql": quarantine_sql,
        "agent_reasoning": agent_reasoning,
        "agent_proposed_actions": state.get("agent_proposed_actions", []),
        "agent_tool_calls": state.get("agent_tool_calls", []),
        "requires_human_approval": state.get("requires_human_approval", False),
        "route_taken": state.get("route_taken", []),
        "run_id": state.get("run_id", ""),
        "root_cause_evidence": state.get("root_cause_evidence", []),
        "root_cause_reasoning": state.get("root_cause_reasoning", ""),
        "upstream_causality_proven": state.get("upstream_causality_proven", False),
        "critic_verdict": state.get("critic_verdict", "APPROVED"),
        "critic_reasoning": state.get("critic_reasoning", ""),
        "critic_retry_count": state.get("critic_retry_count", 0),
    }

    llm_agents = {
        "root_cause": bool(state.get("root_cause_llm_used", False)),
        "triage": bool(state.get("triage_llm_used", False)),
        "critic": bool(state.get("critic_llm_used", False)),
    }

    # ----------------------------------------------------
    # TIER 2D: Distribution & Profiling Metrics (Recharts)
    # ----------------------------------------------------
    input_file = state.get("input_file")
    profiling_metrics = []
    
    if input_file and Path(input_file).exists():
        try:
            profile = profile_stage(input_file)
            cols = profile.get("columns", {})
            
            for col_name, col_data in cols.items():
                col_null_pct = col_data.get("null_percentage", 0.0)
                col_distinct = col_data.get("unique_count", 0)
                col_dtype = col_data.get("dtype", "VARCHAR").upper()
                
                # Determine status based on issues
                col_has_issue = any(iss.get("column") == col_name for iss in issues)
                col_status = "FAILED_EXPECTATION" if col_has_issue else "PASSED"
                
                profiling_metrics.append({
                    "column_name": col_name,
                    "null_percentage": col_null_pct,
                    "distinct_count": col_distinct,
                    "data_type": col_dtype,
                    "status": col_status
                })
        except Exception:
            pass

    data_snapshot: Dict[str, Any] = {"available": False, "rows": [], "columns": []}
    if input_file and Path(input_file).exists():
        try:
            frame = pd.read_csv(input_file) if Path(input_file).suffix.lower() == ".csv" else pd.read_parquet(input_file)
            data_snapshot = {
                "available": True,
                "file_name": Path(input_file).name,
                "row_count": int(len(frame)),
                "column_count": int(len(frame.columns)),
                "columns": [str(column) for column in frame.columns],
                "rows": json.loads(frame.head(8).where(pd.notna(frame.head(8)), None).to_json(orient="records", date_format="iso")),
            }
        except Exception as exc:
            data_snapshot["error"] = str(exc)

    return {
        "pipeline_health": pipeline_health,
        "lineage_graph": lineage_graph,
        "sql_diagnostics": sql_diagnostics,
        "root_cause_analysis": root_cause_analysis,
        "agent_execution": {
            "mode": "LLM_AGENT_FIRST",
            "llm_agents": llm_agents,
            "llm_used": any(llm_agents.values()),
            "fallback_used": not all(llm_agents.values()),
        },
        "profiling_metrics": profiling_metrics,
        "data_snapshot": data_snapshot,
        "remediation": state.get("remediation_result", {}),
        "guardrails": state.get("guardrails_result", {}),
        "workflow_status": state.get("pipeline_status", "UNKNOWN"),
        "issues": issues,
        "run_id": state.get("run_id", ""),
        "requires_human_approval": state.get("requires_human_approval", False),
        "route_taken": state.get("route_taken", []),
    }


@app.get("/api/health")
def api_health():
    return {
        "status": "online",
        "service": "ObsidianDQ Engine",
        "gemini_available": bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")),
        "llm_provider": get_llm_provider(),
        "llm_available": bool(get_llm_provider()),
    }


@app.post("/api/pipeline/run")
def run_pipeline_api(req: Optional[PipelineRunRequest] = None):
    """
    Run ObsidianDQ pipeline and return formatted 3-Tier telemetry response.
    """
    start_time = time.time()
    
    input_file = req.input_file if req and req.input_file else str(PROJECT_ROOT / "data" / "raw" / "stg_orders.parquet")
    sql_file = req.sql_file if req and req.sql_file else str(PROJECT_ROOT / "data" / "queries" / "fct_sales.sql")
    lineage_file = req.lineage_file if req and req.lineage_file else str(PROJECT_ROOT / "data" / "lineage" / "lineage.json")

    # If default data missing, trigger synthetic data generator automatically
    input_path = Path(input_file)
    if not input_path.exists():
        from generate_data import generate_all
        generate_all()

    try:
        final_state = run_pipeline(
            input_file=input_file,
            sql_file=sql_file,
            lineage_file=lineage_file
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Pipeline execution failed: {str(exc)}")

    end_time = time.time()
    duration_ms = int((end_time - start_time) * 1000)

    if isinstance(final_state, dict):
        final_state["lineage_file"] = lineage_file

    RUN_STATES[final_state.get("run_id", "")] = dict(final_state)
    response_data = format_3tier_response(dict(final_state), duration_ms)
    _log_run_history(response_data)
    return response_data


@app.post("/api/pipeline/approve")
def approve_pipeline_action(req: ApprovalRequest):
    """Approve or reject one proposal; approval unblocks the pipeline, not an individual issue."""
    decision = req.decision.lower()
    if decision not in {"approve", "reject"}:
        raise HTTPException(status_code=400, detail="decision must be approve or reject")

    state = RUN_STATES.get(req.run_id)
    if not state:
        raise HTTPException(status_code=404, detail="run_id not found")

    proposal = next((item for item in state.get("agent_proposed_actions", []) if item.get("issue_id") == req.issue_id), None)
    if not proposal:
        raise HTTPException(status_code=404, detail="issue_id not found in run")

    if decision == "reject":
        graph = build_graph()
        config = {"configurable": {"thread_id": req.run_id}}
        graph.update_state(config, {"approval_decision": "reject"})
        resumed_state = graph.invoke(None, config)
        RUN_STATES[req.run_id] = dict(resumed_state)
        return format_3tier_response(dict(resumed_state), 0)

    action = (req.action or proposal.get("action", "FLAG_FOR_REVIEW")).upper()
    graph = build_graph()
    config = {"configurable": {"thread_id": req.run_id}}
    graph.update_state(config, {
        "approval_decision": "approve",
        "approved_issue_id": req.issue_id,
        "approved_action": action,
    })
    resumed_state = graph.invoke(None, config)
    RUN_STATES[req.run_id] = dict(resumed_state)
    return format_3tier_response(dict(resumed_state), 0)


@app.post("/api/pipeline/upload")
async def upload_file_api(
    file: UploadFile = File(...),
    file_type: str = Form("dataset"), # 'dataset', 'sql', or 'lineage'
):
    """
    Handle user uploaded custom CSV/Parquet dataset, SQL query, or Lineage JSON.
    """
    try:
        if file_type not in {"dataset", "sql", "lineage"}:
            raise HTTPException(status_code=400, detail="file_type must be dataset, sql, or lineage")
        suffix = Path(file.filename or "").suffix.lower()
        expected = {"dataset": {".csv", ".parquet"}, "sql": {".sql"}, "lineage": {".json"}}
        if suffix not in expected[file_type]:
            raise HTTPException(status_code=400, detail=f"Unsupported {file_type} file type: {suffix or 'no extension'}")
        save_path = UPLOAD_DIR / f"{file_type}_{int(time.time())}{suffix}"
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")
        preview: Dict[str, Any] = {}
        if file_type == "dataset":
            frame = pd.read_csv(BytesIO(content)) if suffix == ".csv" else pd.read_parquet(BytesIO(content))
            if frame.empty:
                raise HTTPException(status_code=400, detail="Dataset contains no rows")
            preview = {"row_count": int(len(frame)), "column_count": int(len(frame.columns)), "columns": [str(column) for column in frame.columns]}
        elif file_type == "sql":
            sql = content.decode("utf-8").strip()
            if not sql:
                raise HTTPException(status_code=400, detail="SQL file is empty")
            from src.agent.nodes.sql_healer import parse_sql
            parse_sql(sql)
            preview = {"parsed": True}
        else:
            lineage = json.loads(content.decode("utf-8"))
            if not isinstance(lineage, dict) or not isinstance(lineage.get("nodes"), list) or not isinstance(lineage.get("edges"), list):
                raise HTTPException(status_code=400, detail="Lineage JSON requires 'nodes' and 'edges' arrays")
            preview = {"node_count": len(lineage["nodes"]), "edge_count": len(lineage["edges"])}
        save_path.write_bytes(content)

        return {
            "status": "success",
            "filename": file.filename,
            "saved_path": str(save_path),
            "file_type": file_type,
            "preview": preview,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(exc)}")


@app.post("/api/pipeline/quarantine")
def execute_quarantine_api(req: QuarantineRequest):
    """
    Execute 1-click quarantine on affected dataset.
    """
    input_file = req.input_file or str(PROJECT_ROOT / "data" / "raw" / "stg_orders.parquet")
    
    try:
        res = remediate_dq_issues(input_file=input_file, issues=[
            {"severity": "HIGH", "rule": "PRICE_NON_NEGATIVE", "column": "price"},
            {"severity": "HIGH", "rule": "NOT_NULL", "column": "customer_id"}
        ])
        return {
            "status": "SUCCESS",
            "message": "Auto-quarantine script executed successfully.",
            "quarantined_rows": res.get("quarantined_rows", 0),
            "quarantine_file": res.get("quarantine_file")
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Quarantine execution failed: {str(exc)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
