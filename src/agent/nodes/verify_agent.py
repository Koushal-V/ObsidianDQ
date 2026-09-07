"""Post-remediation validation on the immutable cleaned artifact."""

from __future__ import annotations

from typing import Any

from .dq_detect import detect_dq_issues


def verify_remediation_node(state: dict[str, Any]) -> dict[str, Any]:
    cleaned_file = state.get("cleaned_file") or state.get("input_file")
    result = detect_dq_issues(str(cleaned_file))
    before = len(state.get("issues", []))
    after = len(result.get("issues", []))
    passed = after == 0
    details = {"checked_file": str(cleaned_file), "before_issue_count": before, "remaining_issue_count": after, "resolved_count": max(0, before - after)}
    print(f"[VERIFY] Post-remediation DQ check executed: {after} remaining issues.")
    return {"cleaned_file": str(cleaned_file), "post_remediation_dq": result, "verification_passed": passed, "verification_details": details, "verification_recovery_required": not passed}
