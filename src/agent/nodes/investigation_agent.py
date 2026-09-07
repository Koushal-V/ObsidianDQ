"""Tool-using investigation agent. Tools are read-only and every result is auditable."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import pandas as pd

from .lineage_rca import build_graph, find_ancestors, find_descendants, load_lineage
from ..utils.llm import DEFAULT_TEMPERATURE, get_groq_client, get_llm_provider, llm_call_event, llm_model_name
from ..utils.memory import search_similar_incidents


def _load_frame(input_file: str) -> pd.DataFrame:
    return pd.read_csv(input_file) if Path(input_file).suffix.lower() == ".csv" else pd.read_parquet(input_file)


def get_sample_rows(input_file: str, column: str, condition: str) -> dict[str, Any]:
    frame = _load_frame(input_file)
    if column not in frame.columns:
        return {"column": column, "rows": [], "matched_count": 0, "error": "column not found"}
    text = condition.lower()
    if "null" in text or "missing" in text:
        selected = frame[frame[column].isna()]
    elif "negative" in text or "non_negative" in text:
        selected = frame[frame[column] < 0]
    elif "status" in text or "invalid" in text:
        selected = frame[~frame[column].isin({"COMPLETED", "PENDING", "CANCELLED"})]
    elif "duplicate" in text:
        selected = frame[frame.duplicated(subset=[column], keep=False)]
    else:
        selected = frame.head(0)
    sample = selected.head(5)
    return {"column": column, "condition": condition, "rows": json.loads(sample.where(pd.notna(sample), None).to_json(orient="records")), "matched_count": int(len(selected))}


def get_column_stats(input_file: str, column: str) -> dict[str, Any]:
    frame = _load_frame(input_file)
    if column not in frame.columns:
        return {"column": column, "error": "column not found"}
    series = frame[column]
    return {"column": column, "dtype": str(series.dtype), "null_count": int(series.isna().sum()), "distinct_count": int(series.nunique(dropna=True)), "row_count": int(len(series))}


def get_lineage_context(stage: str, lineage_file: str) -> dict[str, Any]:
    lineage = load_lineage(lineage_file)
    graph = build_graph(lineage)
    return {"stage": stage, "direct_upstream": sorted(graph["upstream"].get(stage, set())), "ancestors": find_ancestors(stage, graph["upstream"]), "downstream": find_descendants(stage, graph["downstream"])}


def investigation_agent_node(state: dict[str, Any]) -> dict[str, Any]:
    """Let Groq select read-only tools over multiple turns; fail safely to minimal evidence."""
    issues = state.get("issues", [])
    evidence: list[dict[str, Any]] = []
    llm_events = list(state.get("llm_execution_events", []))
    llm_used = False
    summary = ""
    if not issues:
        return {"investigation_evidence": evidence, "investigation_complete": True, "investigation_llm_used": False, "investigation_summary": "No issues to investigate.", "llm_execution_events": llm_events}

    input_file = state["input_file"]
    lineage_file = state["lineage_file"]
    tool_functions = {
        "get_sample_rows": lambda **a: get_sample_rows(input_file, **a),
        "get_column_stats": lambda **a: get_column_stats(input_file, **a),
        "get_lineage_context": lambda **a: get_lineage_context(lineage_file=lineage_file, **a),
        "search_similar_incidents": lambda **a: {"similar_runs": search_similar_incidents(**a)},
    }
    if get_llm_provider() == "groq":
        client = get_groq_client()
        if not client:
            llm_events.append(llm_call_event("investigation_agent", "groq", success=False, started_at=time.perf_counter(), error="Groq client initialization failed"))
        else:
            declarations = [{"type": "function", "function": {"name": name, "description": "Read-only data quality investigation tool.", "parameters": {"type": "object", "properties": {"column": {"type": "string"}, "condition": {"type": "string"}, "stage": {"type": "string"}, "rule": {"type": "string"}}, "required": []}}} for name in tool_functions]
            messages: list[dict[str, Any]] = [{"role": "system", "content": "You are an investigation agent. Use read-only tools before summarizing. Never propose or execute remediation."}, {"role": "user", "content": json.dumps({"stage": state.get("affected_stage"), "issues": issues, "critic_feedback": state.get("critic_reasoning", "")}, default=str)}]
            try:
                for sequence in range(1, 7):
                    started_at = time.perf_counter()
                    response = None
                    for attempt in range(3):
                        try:
                            response = client.chat.completions.create(model=llm_model_name("groq"), messages=messages, tools=declarations, tool_choice="auto", temperature=DEFAULT_TEMPERATURE, max_tokens=400)
                            break
                        except Exception as exc:
                            if ("rate_limit" in str(exc).lower() or "429" in str(exc)) and attempt < 2:
                                time.sleep(2 * (attempt + 1))
                                continue
                            raise exc
                    llm_events.append(llm_call_event("investigation_agent", "groq", success=True, started_at=started_at))
                    llm_used = True
                    message = response.choices[0].message
                    calls = message.tool_calls or []
                    messages.append(message.model_dump(exclude_none=True))
                    if not calls:
                        if message.content:
                            summary = message.content
                            evidence.append({"type": "agent_summary", "text": summary})
                        break
                    for call in calls:
                        args = json.loads(call.function.arguments or "{}")
                        tool_started = time.perf_counter()
                        try:
                            result = tool_functions[call.function.name](**args)
                            tool_error = None
                        except Exception as exc:
                            result, tool_error = {"error": str(exc)[:500]}, str(exc)
                        evidence.append({"type": "tool", "name": call.function.name, "arguments": args, "result": result, "fallback": False, "sequence": sequence, "timestamp": llm_call_event("tool", "groq", success=True, started_at=tool_started)["timestamp"], "latency_ms": round((time.perf_counter() - tool_started) * 1000, 2), "error": tool_error})
                        messages.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(result, default=str)})
            except Exception as exc:
                llm_events.append(llm_call_event("investigation_agent", "groq", success=False, started_at=started_at if 'started_at' in locals() else time.perf_counter(), error=exc))
                evidence.append({"type": "warning", "text": f"Groq tool investigation unavailable: {exc}"})

    if not any(item.get("type") == "tool" for item in evidence):
        # Safe deterministic evidence is retained only as an offline fallback, never a remediation decision.
        for issue in issues:
            column = str(issue.get("column") or "")
            if column:
                evidence.append({"type": "tool", "name": "get_sample_rows", "arguments": {"column": column, "condition": issue.get("rule", "issue")}, "result": get_sample_rows(input_file, column, str(issue.get("rule", "issue"))), "fallback": True})
                evidence.append({"type": "tool", "name": "search_similar_incidents", "arguments": {"column": column, "rule": str(issue.get("rule", ""))}, "result": {"similar_runs": search_similar_incidents(column, str(issue.get("rule", "")))}, "fallback": True})
        evidence.append({"type": "tool", "name": "get_lineage_context", "arguments": {"stage": state.get("affected_stage", "stg_orders")}, "result": get_lineage_context(state.get("affected_stage", "stg_orders"), lineage_file), "fallback": True})
    print("[INVESTIGATE] Dynamic tool execution completed.")
    return {"investigation_evidence": evidence, "investigation_complete": True, "investigation_llm_used": llm_used, "investigation_summary": summary, "llm_execution_events": llm_events}
