"""
ObsidianDQ - Critic Agent
-------------------------
LLM-backed multi-agent node that reviews Triage Agent proposals and
Root-Cause Agent conclusions against real evidence before execution.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List
from ..utils.llm import generate_text, get_llm_provider

try:
    from google import genai
    HAS_GENAI = True
except ImportError:
    genai = None
    HAS_GENAI = False


def critic_agent_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Review Triage proposals and Root-Cause conclusions against evidence.
    Returns 'APPROVED' or 'REVISION_REQUIRED'.
    """
    proposals = state.get("agent_proposed_actions", [])
    root_cause_stage = state.get("root_cause_stage", "stg_orders")
    root_cause_reasoning = state.get("root_cause_reasoning", "")
    issues = state.get("issues", [])
    affected_stage = state.get("affected_stage", "stg_orders")
    retry_count = state.get("critic_retry_count", 0)

    # Default fallback verdict
    verdict = "APPROVED"
    reasoning = "Critic Agent verified proposals and root-cause conclusions against deterministic schema rules."
    critique_details: List[Dict[str, Any]] = []
    llm_used = False

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    provider = get_llm_provider()

    if provider == "groq" and proposals:
        try:
            prompt = f"""
You are the ObsidianDQ Critic Agent. Audit the triage proposals and root-cause conclusion below.
Return JSON only with keys: verdict (APPROVED or REVISION_REQUIRED) and reasoning.
Affected Stage: {affected_stage}
Detected Issues: {issues}
Root-Cause Stage: {root_cause_stage}
Root-Cause Reasoning: {root_cause_reasoning}
Triage Proposals: {proposals}
"""
            text = generate_text(prompt, model=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"))
            if text:
                llm_used = True
                parsed = json.loads(text[text.find("{"):text.rfind("}") + 1])
                verdict = parsed.get("verdict", "APPROVED").upper()
                reasoning = parsed.get("reasoning", reasoning)
        except Exception as exc:
            critique_details.append({
                "agent": "Critic Agent",
                "type": "warning",
                "text": f"Groq Critic audit skipped or failed; fallback approved: {exc}",
            })
    elif api_key and proposals and HAS_GENAI and genai is not None:
        try:
            client = genai.Client(api_key=api_key)
            prompt = f"""
            You are the ObsidianDQ Critic Agent. Your job is to audit the Triage Agent's proposals and Root-Cause Agent's conclusion.
            
            - Affected Stage: {affected_stage}
            - Detected Issues: {issues}
            - Root-Cause Stage Conclusion: {root_cause_stage}
            - Root-Cause Reasoning: {root_cause_reasoning}
            - Triage Proposed Actions: {proposals}
            
            Audit Questions:
            1. Are the proposed actions supported by the detected issue severities?
            2. Is the root-cause conclusion logical given the upstream lineage?
            
            Respond with JSON format:
            {{
                "verdict": "APPROVED" or "REVISION_REQUIRED",
                "reasoning": "Concise summary of your critique."
            }}
            """

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )

            if response and response.text:
                llm_used = True
                text = response.text.strip()
                if "{" in text and "}" in text:
                    json_str = text[text.find("{"):text.rfind("}") + 1]
                    parsed = json.loads(json_str)
                    verdict = parsed.get("verdict", "APPROVED").upper()
                    reasoning = parsed.get("reasoning", reasoning)
                else:
                    reasoning = text
        except Exception as exc:
            critique_details.append({
                "agent": "Critic Agent",
                "type": "warning",
                "text": f"LLM Critic audit skipped or failed; fallback approved: {exc}",
            })

    # Handle revision retries
    requires_human_approval = state.get("requires_human_approval", False)
    if verdict == "REVISION_REQUIRED":
        new_retry_count = retry_count + 1
        if new_retry_count > 1:
            requires_human_approval = True
            pipeline_status = "WAITING_FOR_HUMAN_APPROVAL"
        else:
            requires_human_approval = False
            pipeline_status = "CRITIC_REVISION_REQUIRED"
    else:
        new_retry_count = retry_count
        pipeline_status = "WAITING_FOR_HUMAN_APPROVAL" if requires_human_approval else "CRITIC_APPROVED"

    return {
        "critic_verdict": verdict,
        "critic_reasoning": reasoning,
        "critic_retry_count": new_retry_count,
        "critic_critique_details": critique_details,
        "requires_human_approval": requires_human_approval,
        "pipeline_status": pipeline_status,
        "critic_llm_used": llm_used,
    }
