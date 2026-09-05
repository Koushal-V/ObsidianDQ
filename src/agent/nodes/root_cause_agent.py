"""
ObsidianDQ - Root Cause Investigator Agent
--------------------------------------------
LLM-backed multi-agent node that investigates upstream lineage graph ancestors
to determine the true origin stage of data-quality failures.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable, Dict, List

import pandas as pd
from .lineage_rca import build_graph, find_ancestors, find_descendants, load_lineage
from ..utils.llm import generate_text, get_llm_provider

try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    genai = None
    types = None
    HAS_GENAI = False


def _load_frame(input_file: str) -> pd.DataFrame:
    path = Path(input_file)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    return pd.read_parquet(path)


def _sample_rows(input_file: str, column: str, condition: str) -> Dict[str, Any]:
    try:
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
            selected = frame.head(5)

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
    except Exception as exc:
        return {"error": str(exc)}


def _lineage_context(stage: str, lineage_file: str) -> Dict[str, Any]:
    try:
        lineage = load_lineage(lineage_file)
        graph = build_graph(lineage)
        return {
            "stage": stage,
            "direct_upstream": sorted(graph["upstream"].get(stage, set())),
            "upstream_ancestors": find_ancestors(stage, graph["upstream"]),
            "downstream_descendants": find_descendants(stage, graph["downstream"]),
        }
    except Exception as exc:
        return {"stage": stage, "error": str(exc)}


def root_cause_agent_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Investigate upstream ancestors using LLM tool reasoning to isolate the true root-cause stage.
    """
    affected_stage = state.get("affected_stage", "stg_orders")
    upstream_ancestors = state.get("upstream_ancestors", [])
    issues = state.get("issues", [])
    lineage_file = state.get("lineage_file", "data/lineage/lineage.json")
    input_file = state.get("input_file", "data/raw/stg_orders.parquet")
    critic_verdict = state.get("critic_verdict")
    critic_reasoning = state.get("critic_reasoning")

    evidence_trail: List[Dict[str, Any]] = []
    root_cause_stage = affected_stage
    reasoning = ""
    proven = False
    llm_concluded = False

    tools: Dict[str, Callable[..., Dict[str, Any]]] = {
        "get_sample_rows": lambda column, condition: _sample_rows(input_file, column, condition),
        "get_lineage_context": lambda stage: _lineage_context(stage, lineage_file),
    }

    def conclude_root_cause(
        root_cause_stage: str = "",
        reasoning: str = "",
        causality_proven: bool = True,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        nonlocal root_cause_stage_out, reasoning_out, proven_out, llm_concluded
        stage_val = root_cause_stage or kwargs.get("root_cause_stage_val") or kwargs.get("stage") or affected_stage
        reason_val = reasoning or kwargs.get("reasoning_val") or kwargs.get("text") or ""
        if "causality_proven" in kwargs:
            proven_val = bool(kwargs["causality_proven"])
        elif "causality_proven_val" in kwargs:
            proven_val = bool(kwargs["causality_proven_val"])
        else:
            proven_val = bool(causality_proven)

        root_cause_stage_out = str(stage_val)
        reasoning_out = str(reason_val)
        proven_out = proven_val
        llm_concluded = True
        return {
            "root_cause_stage": root_cause_stage_out,
            "reasoning": reasoning_out,
            "causality_proven": proven_out,
        }

    root_cause_stage_out = root_cause_stage
    reasoning_out = reasoning
    proven_out = proven

    tools["conclude_root_cause"] = conclude_root_cause

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    provider = get_llm_provider()

    if provider == "groq" and issues:
        try:
            evidence = []
            for issue in issues:
                column = str(issue.get("column") or "")
                evidence.append({
                    "issue": issue,
                    "sample_rows": _sample_rows(input_file, column, str(issue.get("rule", "issue"))),
                    "lineage": _lineage_context(affected_stage, lineage_file),
                })
            prompt = f"""
You are the ObsidianDQ Root-Cause Investigator Agent. Identify the earliest upstream stage that likely introduced the issue.
Return JSON only with keys root_cause_stage, reasoning, and causality_proven.
Affected stage: {affected_stage}
Upstream ancestors: {upstream_ancestors}
Evidence: {json.dumps(evidence, default=str)}
"""
            text = generate_text(prompt, model=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"))
            if text:
                parsed = json.loads(text[text.find("{"):text.rfind("}") + 1])
                conclude_root_cause(**parsed)
        except Exception as exc:
            evidence_trail.append({
                "agent": "Root-Cause Investigator Agent",
                "type": "warning",
                "text": f"Groq investigation warning; fallback deterministic root-cause used: {exc}",
            })
    elif api_key and issues and HAS_GENAI and genai is not None:
        try:
            declarations = [
                types.FunctionDeclaration(
                    name="get_sample_rows",
                    description="Read up to 5 actual offending rows from the dataset.",
                    parameters_json_schema={"type": "object", "properties": {"column": {"type": "string"}, "condition": {"type": "string"}}, "required": ["column", "condition"]},
                ),
                types.FunctionDeclaration(
                    name="get_lineage_context",
                    description="Inspect direct and transitive upstream/downstream lineage.",
                    parameters_json_schema={"type": "object", "properties": {"stage": {"type": "string"}}, "required": ["stage"]},
                ),
                types.FunctionDeclaration(
                    name="conclude_root_cause",
                    description="Record the concluded root-cause stage, technical reasoning narrative, and whether causality is proven.",
                    parameters_json_schema={
                        "type": "object",
                        "properties": {
                            "root_cause_stage": {"type": "string"},
                            "reasoning": {"type": "string"},
                            "causality_proven": {"type": "boolean"},
                        },
                        "required": ["root_cause_stage", "reasoning", "causality_proven"],
                    },
                ),
            ]

            client = genai.Client(api_key=api_key)
            prompt = (
                "You are the ObsidianDQ Root-Cause Investigator Agent.\n"
                "Your job is to analyze upstream data lineage and evidence to identify which stage introduced data corruption.\n"
                f"- Affected Stage: {affected_stage}\n"
                f"- Upstream Ancestors: {upstream_ancestors}\n"
                f"- Detected Issues: {issues}\n"
            )

            if critic_verdict == "REVISION_REQUIRED" and critic_reasoning:
                prompt += f"\nCRITIC REVISION REQUEST: A previous conclusion was flagged by Critic Agent with reasoning: '{critic_reasoning}'. Please re-evaluate evidence and refine your conclusion.\n"

            prompt += (
                "Call get_sample_rows or get_lineage_context to gather evidence per ancestor. "
                "Finally, call conclude_root_cause(root_cause_stage, reasoning, causality_proven) to finalize your conclusion."
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
                    if response.text and not reasoning_out:
                        reasoning_out = response.text.strip()
                    break
                responses = []
                for call in calls:
                    name = call.name
                    args = dict(call.args or {})
                    result = tools[name](**args)
                    record = {
                        "agent": "Root-Cause Investigator Agent",
                        "type": "tool",
                        "name": name,
                        "arguments": args,
                        "result": result,
                        "text": f"Called {name} with {args}",
                    }
                    evidence_trail.append(record)
                    responses.append(types.Part.from_function_response(name=name, response=result))
                contents.append(types.Content(role="user", parts=responses))
                if llm_concluded:
                    break

        except Exception as exc:
            evidence_trail.append({
                "agent": "Root-Cause Investigator Agent",
                "type": "warning",
                "text": f"LLM investigation warning; fallback deterministic root-cause used: {exc}",
            })

    # Deterministic fallback if LLM did not reach a structured conclusion via conclude_root_cause
    if not llm_concluded:
        if upstream_ancestors:
            root_cause_stage_out = upstream_ancestors[0]
            reasoning_out = f"Upstream lineage traversal isolated candidate stage '{root_cause_stage_out}' as the earliest ancestor feeding '{affected_stage}' (fallback)."
            proven_out = False
            evidence_trail.append({
                "agent": "Root-Cause Investigator Agent",
                "type": "lineage_traversal",
                "stage": root_cause_stage_out,
                "text": f"Lineage ancestor '{root_cause_stage_out}' feeds into '{affected_stage}' (unproven fallback).",
            })
        else:
            root_cause_stage_out = affected_stage
            reasoning_out = f"Anomalies detected in '{affected_stage}'. Upstream causality has not been proven."
            proven_out = False

    return {
        "root_cause_stage": root_cause_stage_out,
        "root_cause_evidence": evidence_trail,
        "root_cause_reasoning": reasoning_out,
        "upstream_causality_proven": proven_out,
        "potential_root_causes": upstream_ancestors if upstream_ancestors else [affected_stage],
        "root_cause_llm_used": llm_concluded,
    }
