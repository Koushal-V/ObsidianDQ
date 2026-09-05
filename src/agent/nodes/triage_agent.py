"""LLM triage node with auditable, read-only tools and proposal output."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from .lineage_rca import build_graph, find_ancestors, find_descendants, load_lineage
from ..utils.llm import generate_text, get_llm_provider

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

    if not issues:
        return {
            "agent_reasoning": [{"type": "decision", "text": "No DQ issues were found; skipping triage."}],
            "agent_tool_calls": [],
            "agent_proposed_actions": [],
            "requires_human_approval": False,
            "route_taken": state.get("route_taken", []) + ["no_issues"],
            "triage_llm_used": False,
        }

    tools: dict[str, Callable[..., dict[str, Any]]] = {
        "get_sample_rows": lambda column, condition: _sample_rows(state["input_file"], column, condition),
        "get_lineage_context": lambda stage: _lineage_context(stage, state["lineage_file"]),
        "get_column_history": _column_history,
    }

    def propose_action(issue_id: str, action: str, confidence: float, reasoning: str) -> dict[str, Any]:
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
            evidence = []
            for issue in issues:
                column = str(issue.get("column") or "")
                condition = str(issue.get("rule", "issue"))
                evidence.append({
                    "issue": issue,
                    "sample_rows": _sample_rows(state["input_file"], column, condition),
                    "lineage": _lineage_context(state.get("affected_stage", "stg_orders"), state["lineage_file"]),
                    "history": _column_history(column),
                })
            prompt = f"""
You are the ObsidianDQ Triage Agent. Inspect the supplied data-quality issues and evidence.
Choose exactly one action for every issue: AUTO_QUARANTINE, FLAG_FOR_REVIEW, IGNORE_TRANSIENT, or ESCALATE_UPSTREAM.
Return JSON only as {{\"proposals\":[{{\"issue_id\":\"RULE:column\",\"action\":\"...\",\"confidence\":0.0,\"reasoning\":\"...\"}}]}}.
Never execute remediation.
Evidence: {json.dumps(evidence, default=str)}
"""
            text = generate_text(prompt, model=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"))
            if text:
                parsed = json.loads(text[text.find("{"):text.rfind("}") + 1])
                for proposal in parsed.get("proposals", []):
                    tools["propose_action"](**proposal)
                    initial_trace.append({"type": "decision", "text": "Groq Triage Agent produced a structured proposal."})
                llm_used = bool(proposals)
        except Exception as exc:
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
                "propose_action exactly once for every issue. Never execute remediation.\n"
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

    requires_approval = any(
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
    }
