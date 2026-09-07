"""Generate a reviewable, LLM-authored remediation plan before execution."""

from __future__ import annotations

import json
import os
from typing import Any

from ..utils.llm import generate_text_with_audit, get_llm_provider, llm_model_name


REQUIRED_STEP_TYPES = ("INVESTIGATE", "SQL_HEAL", "QUARANTINE", "VERIFY")


def _safe_baseline_plan(state: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"step": 1, "type": "INVESTIGATE", "target": state.get("root_cause_stage", state.get("affected_stage")), "description": "Confirm evidence and upstream ownership before execution."},
        {"step": 2, "type": "SQL_HEAL", "target": state.get("sql_file"), "description": "Apply only deterministic AST-validated SQL repairs."},
        {"step": 3, "type": "QUARANTINE", "target": state.get("affected_stage"), "description": "Apply approved containment actions without mutating source data."},
        {"step": 4, "type": "VERIFY", "target": state.get("affected_stage"), "description": "Re-run deterministic DQ checks on the cleaned artifact."},
    ]


def planning_agent_node(state: dict[str, Any]) -> dict[str, Any]:
    issues = state.get("issues", [])
    risk = "HIGH" if any(str(issue.get("severity")).upper() == "HIGH" for issue in issues) else "MEDIUM" if issues else "LOW"
    steps = _safe_baseline_plan(state) if issues else []
    llm_used = False
    llm_events = list(state.get("llm_execution_events", []))

    if issues and get_llm_provider() == "groq":
        request = {
            "role": "ObsidianDQ Planning Agent",
            "instruction": "Create a structured remediation plan only; do not execute any action. Include every required step type.",
            "root_cause_stage": state.get("root_cause_stage"),
            "issues": issues,
            "investigation_evidence": state.get("investigation_evidence", []),
            "required_step_types": REQUIRED_STEP_TYPES,
            "response_schema": {"steps": [{"step": 1, "type": "INVESTIGATE", "target": "string", "description": "string"}], "plan_risk_level": "LOW|MEDIUM|HIGH"},
        }
        try:
            text, event = generate_text_with_audit(json.dumps(request, default=str), stage="planning_agent", model=llm_model_name("groq"))
            llm_events.append(event)
            parsed = json.loads(text[text.find("{"):text.rfind("}") + 1]) if text else {}
            candidate = parsed.get("steps", [])
            proposed_types = [item.get("type") for item in candidate if isinstance(item, dict)]
            if all(step_type in proposed_types for step_type in REQUIRED_STEP_TYPES):
                steps = candidate
                llm_used = True
        except Exception:
            pass

    approvals = ["human approval required for medium/high risk or low-confidence triage"] if risk != "LOW" else []
    print(f"[PLAN] Generated {len(steps)}-step remediation & verification plan.")
    return {"remediation_plan": steps, "required_approvals": approvals, "plan_risk_level": risk, "planning_llm_used": llm_used, "llm_execution_events": llm_events}
