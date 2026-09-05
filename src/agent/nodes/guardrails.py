from typing import Any, Dict


def validate_dq_result(dq_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate the structure of the DQ detector result.

    Expected DQ result structure:
        row_count
        issue_count
        severity_summary
        issues

    Each issue should contain:
        rule
        column
        issue
        count
        severity
    """

    errors = []
    warnings = []

    if not isinstance(dq_result, dict):
        return {
            "valid": False,
            "errors": ["DQ result must be a dictionary"],
            "warnings": [],
        }

    # --------------------------------------------------------
    # Validate row count
    # --------------------------------------------------------

    if "row_count" not in dq_result:
        errors.append("Missing 'row_count' field")
    else:
        if not isinstance(dq_result["row_count"], int):
            errors.append("'row_count' must be an integer")
        elif dq_result["row_count"] < 0:
            errors.append("'row_count' cannot be negative")

    # --------------------------------------------------------
    # Validate issues
    # --------------------------------------------------------

    issues = dq_result.get("issues")

    if issues is None:
        errors.append("Missing 'issues' field")
        issues = []

    elif not isinstance(issues, list):
        errors.append("'issues' must be a list")
        issues = []

    # --------------------------------------------------------
    # Validate individual issues
    # --------------------------------------------------------

    allowed_severities = {"HIGH", "MEDIUM", "LOW"}

    for index, issue in enumerate(issues, start=1):

        if not isinstance(issue, dict):
            errors.append(f"Issue {index} must be a dictionary")
            continue

        required_fields = [
            "rule",
            "column",
            "count",
            "severity",
        ]

        for field in required_fields:
            if field not in issue:
                errors.append(
                    f"Issue {index} missing '{field}'"
                )

        if "issue" not in issue and "description" not in issue:
            errors.append(f"Issue {index} missing 'issue' or 'description'")

        # Severity validation
        severity = issue.get("severity")

        if severity is not None:
            if severity not in allowed_severities:
                errors.append(
                    f"Issue {index} has invalid severity: "
                    f"{severity}"
                )

        # Count validation
        count = issue.get("count")

        if count is not None:
            if not isinstance(count, int):
                errors.append(
                    f"Issue {index} 'count' must be an integer"
                )
            elif count < 0:
                errors.append(
                    f"Issue {index} 'count' cannot be negative"
                )

    # --------------------------------------------------------
    # Validate issue count
    # --------------------------------------------------------

    issue_count = dq_result.get("issue_count")

    if issue_count is None:
        errors.append("Missing 'issue_count' field")

    elif not isinstance(issue_count, int):
        errors.append("'issue_count' must be an integer")

    elif issue_count != len(issues):
        errors.append(
            f"'issue_count' ({issue_count}) does not match "
            f"number of issues ({len(issues)})"
        )

    # --------------------------------------------------------
    # Validate severity summary
    # --------------------------------------------------------

    severity_summary = dq_result.get("severity_summary")

    if severity_summary is None:
        errors.append("Missing 'severity_summary' field")

    elif not isinstance(severity_summary, dict):
        errors.append("'severity_summary' must be a dictionary")

    else:
        for severity in allowed_severities:
            value = severity_summary.get(severity, 0)

            if not isinstance(value, int):
                errors.append(
                    f"Severity summary '{severity}' must be an integer"
                )

            elif value < 0:
                errors.append(
                    f"Severity summary '{severity}' cannot be negative"
                )

    # --------------------------------------------------------
    # Warnings
    # --------------------------------------------------------

    high_severity_issues = [
        issue
        for issue in issues
        if isinstance(issue, dict)
        and issue.get("severity") == "HIGH"
    ]

    if high_severity_issues:
        high_rules = ", ".join(
            issue.get("rule", "UNKNOWN")
            for issue in high_severity_issues
        )

        warnings.append(
            f"High-severity issue detected: {high_rules}"
        )

    # --------------------------------------------------------
    # Final validation result
    # --------------------------------------------------------

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }


def apply_guardrails(
    dq_result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Apply deterministic guardrails to the DQ result.

    HIGH severity issues trigger controlled remediation.
    Invalid DQ results are blocked.
    """

    validation = validate_dq_result(dq_result)

    errors = validation.get("errors", [])
    warnings = validation.get("warnings", [])

    # Invalid DQ structure
    if errors:
        return {
            "approved": False,
            "action": "BLOCK",
            "errors": errors,
            "warnings": warnings,
        }

    issues = dq_result.get("issues", [])

    high_severity = any(
        issue.get("severity") == "HIGH"
        for issue in issues
        if isinstance(issue, dict)
    )

    # HIGH severity → controlled remediation
    if high_severity:
        return {
            "approved": True,
            "action": "CONTROLLED_REMEDIATION",
            "errors": [],
            "warnings": warnings,
        }

    # No HIGH severity issues
    return {
        "approved": True,
        "action": "REMEDIATE",
        "errors": [],
        "warnings": warnings,
    }


def print_guardrails_result(
    result: Dict[str, Any],
) -> None:
    """Print guardrails result."""

    print("\nGuardrails Result")
    print("=" * 60)

    print("Approved:", result.get("approved", False))
    print("Action:", result.get("action", "BLOCK"))
    print("Errors:", result.get("errors", []))
    print("Warnings:", result.get("warnings", []))