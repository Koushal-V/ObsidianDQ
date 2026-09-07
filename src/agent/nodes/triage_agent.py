"""LLM triage node with auditable, read-only tools and proposal output."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from .lineage_rca import build_graph, find_ancestors, find_descendants, load_lineage
from ..utils.llm import DEFAULT_TEMPERATURE, generate_text, get_groq_client, get_llm_provider, llm_call_event, llm_model_name

ACTIONS = {
    "AUTO_QUARANTINE",
    "FLAG_FOR_REVIEW",
    "IGNORE_TRANSIENT",
    "ESCALATE_UPSTREAM",
}


def _load_frame(input_file: str) -> pd.DataFrame:
    path = Path(input_file)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    return pd.read_parquet(path)


def _sample_rows(input_file: str, column: str, condition: str) -> dict[str, Any]:
    frame = _load_frame(input_file)
    condition = condition.lower()
    if column not in frame.columns:
        return {"error": f"Column not found: {column}"}

    if "null" in condition or "missing" in condition:
        selected = frame[frame[column].isna()]
    elif "negative" in condition:
        selected = frame[frame[column] < 0]
    elif "status" in condition or "invalid" in condition:
        selected = frame[~frame[column].isin({"COMPLETED", "PENDING", "CANCELLED"})]
    elif "duplicate" in condition:
        selected = frame[frame.duplicated(subset=[column], keep=False)]
    else:
        selected = frame.head(0)

    return {
        "column": column,
        "condition": condition,
        "rows": json.loads(
            selected.head(5).where(pd.notna(selected.head(5)), None).to_json(
                orient="records",
                date_format="iso",
            )
        ),
        "matched_count": int(len(selected)),
    }


def _lineage_context(stage: str, lineage_file: str) -> dict[str, Any]:
    lineage = load_lineage(lineage_file)
    graph = build_graph(lineage)
    return {
        "stage": stage,
        "direct_upstream": sorted(graph["upstream"].get(stage, set())),
        "upstream_ancestors": find_ancestors(stage, graph["upstream"]),
        "downstream_descendants": find_descendants(stage, graph["downstream"]),
    }


def _column_history(column: str) -> dict[str, Any]:
    history_file = Path(__file__).resolve().parents[3] / "data" / "run_history.jsonl"
    if not history_file.exists():
        return {"column": column, "runs": 0, "message": "No run history is available yet."}

    matches = []
    for line in history_file.read_text(encoding="utf-8").splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if column in record.get("failed_columns", []):
            matches.append(record)
    return {"column": column, "runs": len(matches), "recent": matches[-5:]}


def triage_agent_node(state: dict[str, Any]) -> dict[str, Any]:
    """Ask Gemini to inspect issue evidence and propose actions, never execute them."""
    issues = state.get("issues", [])
    initial_trace: list[dict[str, Any]] = []
    tool_calls: list[dict[str, Any]] = []
    proposals: list[dict[str, Any]] = []
    llm_used = False
    llm_events = list(state.get("llm_execution_events", []))

    if not issues:
        return {
            "agent_reasoning": [{"type": "decision", "text": "No DQ issues were found; skipping triage."}],
            "agent_tool_calls": [],
            "agent_proposed_actions": [],
            "requires_human_approval": False,
            "route_taken": state.get("route_taken", []) + ["no_issues"],
            "triage_llm_used": False,
            "llm_execution_events": llm_events,
        }

    tools: dict[str, Callable[..., dict[str, Any]]] = {
        "get_sample_rows": lambda column, condition: _sample_rows(state["input_file"], column, condition),
        "get_lineage_context": lambda stage: _lineage_context(stage, state["lineage_file"]),
        "get_column_history": _column_history,
    }

    def propose_action(issue_id: str, action: str, confidence: float, reasoning: str) -> dict[str, Any]:
        # Unknown identifiers are kept visible and fail closed in the coverage pass below.
        issue_id = str(issue_id)
        normalized = str(action).upper()
        proposal = {
            "issue_id": issue_id,
            "action": normalized if normalized in ACTIONS else "FLAG_FOR_REVIEW",
            "confidence": max(0.0, min(1.0, float(confidence))),
            "reasoning": str(reasoning),
        }
        proposals.append(proposal)
        return proposal

    tools["propose_action"] = propose_action
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    provider = get_llm_provider()

    if provider == "groq":
        try:
            client = get_groq_client()
            if not client:
                llm_events.append(llm_call_event("triage_agent", "groq", success=False, started_at=time.perf_counter(), error="Groq client initialization failed"))
                raise RuntimeError("Groq client is unavailable")
            declarations = [
                {"type": "function", "function": {"name": "get_sample_rows", "description": "Read actual offending rows.", "parameters": {"type": "object", "properties": {"column": {"type": "string"}, "condition": {"type": "string"}}, "required": ["column", "condition"]}}},
                {"type": "function", "function": {"name": "get_lineage_context", "description": "Read lineage context.", "parameters": {"type": "object", "properties": {"stage": {"type": "string"}}, "required": ["stage"]}}},
                {"type": "function", "function": {"name": "get_column_history", "description": "Read prior incidents.", "parameters": {"type": "object", "properties": {"column": {"type": "string"}}, "required": ["column"]}}},
                {"type": "function", "function": {"name": "propose_action", "description": "Record a non-executing proposal for an exact issue id.", "parameters": {"type": "object", "properties": {"issue_id": {"type": "string"}, "action": {"type": "string", "enum": sorted(ACTIONS)}, "confidence": {"type": "number"}, "reasoning": {"type": "string"}}, "required": ["issue_id", "action", "confidence", "reasoning"]}}},
            ]
            critique = state.get("critic_reasoning", "") if state.get("critic_verdict") == "REVISION_REQUIRED" else ""
            messages: list[dict[str, Any]] = [
                {"role": "system", "content": "Dynamically select read-only tools before calling propose_action exactly once per issue. Never execute remediation."},
                {"role": "user", "content": json.dumps({"stage": state.get("affected_stage"), "issues": issues, "critic_feedback": critique}, default=str)},
            ]
            for _ in range(8):
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
                llm_events.append(llm_call_event("triage_agent", "groq", success=True, started_at=started_at))
                message = response.choices[0].message
                messages.append(message.model_dump(exclude_none=True))
                calls = message.tool_calls or []
                if not calls:
                    if message.content:
                        initial_trace.append({"type": "decision", "text": message.content})
                    break
                for call in calls:
                    args = json.loads(call.function.arguments or "{}")
                    tool_started = time.perf_counter()
                    try:
                        result = tools[call.function.name](**args)
                        tool_error = None
                    except Exception as exc:
                        result, tool_error = {"error": str(exc)[:500]}, str(exc)
                    tool_calls.append({"name": call.function.name, "arguments": args, "result": result, "fallback": False, "sequence": len(tool_calls) + 1, "timestamp": llm_call_event("tool", "groq", success=True, started_at=tool_started)["timestamp"], "latency_ms": round((time.perf_counter() - tool_started) * 1000, 2), "error": tool_error})
                    initial_trace.append({"type": "tool", "text": f"Called {call.function.name} with {args}", "result": result})
                    messages.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(result, default=str)})
                    if call.function.name == "propose_action":
                        llm_used = True
        except Exception as exc:
            if 'started_at' in locals() and not (llm_events and llm_events[-1].get("success") is False):
                llm_events.append(llm_call_event("triage_agent", "groq", success=False, started_at=started_at, error=exc))
            initial_trace.append({"type": "warning", "text": f"Groq triage unavailable; deterministic fallback used: {exc}"})
    elif api_key:
        try:
            from google import genai
            from google.genai import types

            declarations = [
                types.FunctionDeclaration(
                    name="get_sample_rows",
                    description="Read up to five actual offending rows from the input dataset.",
                    parameters_json_schema={"type": "object", "properties": {"column": {"type": "string"}, "condition": {"type": "string"}}, "required": ["column", "condition"]},
                ),
                types.FunctionDeclaration(
                    name="get_lineage_context",
                    description="Inspect direct and transitive upstream/downstream lineage.",
                    parameters_json_schema={"type": "object", "properties": {"stage": {"type": "string"}}, "required": ["stage"]},
                ),
                types.FunctionDeclaration(
                    name="get_column_history",
                    description="Check whether a column has failed in prior recorded runs.",
                    parameters_json_schema={"type": "object", "properties": {"column": {"type": "string"}}, "required": ["column"]},
                ),
                types.FunctionDeclaration(
                    name="propose_action",
                    description="Record exactly one triage proposal for one issue; proposals are not execution.",
                    parameters_json_schema={"type": "object", "properties": {"issue_id": {"type": "string"}, "action": {"type": "string", "enum": sorted(ACTIONS)}, "confidence": {"type": "number"}, "reasoning": {"type": "string"}}, "required": ["issue_id", "action", "confidence", "reasoning"]},
                ),
            ]
            client = genai.Client(api_key=api_key)
            critic_verdict = state.get("critic_verdict")
            critic_reasoning = state.get("critic_reasoning")
            critic_context = f"\nCRITIC REVISION REQUEST: A previous proposal was flagged by Critic Agent with reasoning: '{critic_reasoning}'. Please refine your proposals.\n" if (critic_verdict == "REVISION_REQUIRED" and critic_reasoning) else ""

            prompt = (
                "You are the ObsidianDQ triage agent. Inspect real evidence with tools before deciding. "
                "Call get_sample_rows, get_lineage_context, or get_column_history as useful, then call "
                "propose_action exactly once for every issue. The issue_id MUST exactly match 'RULE:column' from the supplied issue. Never execute remediation.\n"
                + critic_context
                + json.dumps({"stage": state.get("affected_stage"), "issues": issues}, default=str)
            )
            contents: list[Any] = [types.Content(role="user", parts=[types.Part.from_text(text=prompt)])]
            config = types.GenerateContentConfig(
                temperature=0.1,
                tools=[types.Tool(function_declarations=declarations)],
            )

            for _ in range(8):
                response = client.models.generate_content(model="gemini-2.5-flash", contents=contents, config=config)
                candidate = response.candidates[0]
                contents.append(candidate.content)
                calls = [part.function_call for part in candidate.content.parts if part.function_call]
                if not calls:
                    if response.text:
                        initial_trace.append({"type": "decision", "text": response.text.strip()})
                    break
                responses = []
                for call in calls:
                    name = call.name
                    args = dict(call.args or {})
                    result = tools[name](**args)
                    if name == "propose_action":
                        llm_used = True
                    record = {"name": name, "arguments": args, "result": result}
                    tool_calls.append(record)
                    initial_trace.append({"type": "tool", "text": f"Called {name} with {args}", "result": result})
                    responses.append(types.Part.from_function_response(name=name, response=result))
                contents.append(types.Content(role="user", parts=responses))
        except Exception as exc:
            initial_trace.append({"type": "warning", "text": f"LLM triage unavailable; deterministic fallback used: {exc}"})

    if not proposals:
        for index, issue in enumerate(issues):
            issue_id = f"{issue.get('rule', 'ISSUE')}:{issue.get('column') or index}"
            severity = str(issue.get("severity", "LOW")).upper()
            action = "FLAG_FOR_REVIEW"
            proposals.append({
                "issue_id": issue_id,
                "action": action,
                "confidence": 0.0,
                "reasoning": f"LLM unavailable; {severity} issue requires explicit human review.",
            })
            initial_trace.append({"type": "decision", "text": f"Proposed {action} for {issue_id}."})

    for index, issue in enumerate(issues):
        issue_id = f"{issue.get('rule', 'ISSUE')}:{issue.get('column') or index}"
        rule = str(issue.get("rule", "ISSUE"))
        column = str(issue.get("column") or "")
        covered = any(
            item.get("issue_id") == issue_id
            or item.get("issue_id") == f"{rule}:{column}"
            for item in proposals
        )
        if not covered:
            proposals.append({
                "issue_id": issue_id,
                "action": "FLAG_FOR_REVIEW",
                "confidence": 0.0,
                "reasoning": "No proposal was returned for this issue.",
            })

    # High-risk plans and uncertain proposals always require a checkpointed
    # human decision. An LLM confidence value can never bypass this gate.
    requires_approval = state.get("plan_risk_level") == "HIGH" or any(
        item["action"] == "FLAG_FOR_REVIEW" or item["confidence"] < 0.7
        for item in proposals
    )
    if any(item["action"] == "ESCALATE_UPSTREAM" for item in proposals) and state.get("escalation_count", 0) == 0:
        route = "escalate"
    elif requires_approval:
        route = "needs_human_review"
    else:
        route = "auto_remediate"

    return {
        "agent_reasoning": initial_trace,
        "agent_tool_calls": tool_calls,
        "agent_proposed_actions": proposals,
        "requires_human_approval": requires_approval,
        "pipeline_status": "WAITING_FOR_HUMAN_APPROVAL" if requires_approval else "TRIAGE_COMPLETE",
        "route_taken": state.get("route_taken", []) + [route],
        "escalation_count": state.get("escalation_count", 0) + (1 if route == "escalate" else 0),
        "triage_llm_used": llm_used,
        "llm_execution_events": llm_events,
    }
