"""
ObsidianDQ - Remediation Node

Takes detected DQ issues and creates remediation actions.
High-severity issues can be quarantined instead of modifying
the original data directly.
"""

from pathlib import Path
import pandas as pd


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

INPUT_FILE = "data/raw/stg_orders.parquet"
QUARANTINE_DIR = Path("data/quarantine")


# ---------------------------------------------------------
# Main remediation function
# ---------------------------------------------------------

def remediate_dq_issues(
    input_file: str = INPUT_FILE,
    issues: list | None = None,
    agent_actions: list | None = None,
) -> dict:
    """
    Apply remediation decisions based on detected DQ issues.

    Parameters
    ----------
    input_file : str
        Path to the affected dataset.

    issues : list
        List of DQ issue dictionaries.

    agent_actions : list
        Structured action proposals produced by the triage agent.

    Returns
    -------
    dict
        Remediation result.
    """

    if issues is None:
        issues = []
    if agent_actions is None:
        agent_actions = []

    actions_by_issue = {
        item.get("issue_id"): item
        for item in agent_actions
        if isinstance(item, dict) and item.get("issue_id")
    }

    input_path = Path(input_file)

    if not input_path.exists():
        raise FileNotFoundError(
            f"Input dataset not found: {input_file}"
        )

    if input_path.suffix.lower() == ".csv":
        df = pd.read_csv(input_path)
    elif input_path.suffix.lower() == ".parquet":
        df = pd.read_parquet(input_path)
    else:
        try:
            df = pd.read_parquet(input_path)
        except Exception:
            df = pd.read_csv(input_path)


    actions = []
    quarantined_rows = pd.DataFrame()

    # -----------------------------------------------------
    # Process each detected issue
    # -----------------------------------------------------

    for issue in issues:

        severity = str(
            issue.get("severity", "LOW")
        ).upper()

        rule = str(
            issue.get("rule", "")
        ).upper()

        column = issue.get("column")
        issue_id = f"{issue.get('rule', 'ISSUE')}:{column or issues.index(issue)}"
        proposal = actions_by_issue.get(issue_id, {})
        proposed_action = str(proposal.get("action", "")).upper()
        force_quarantine = proposed_action == "AUTO_QUARANTINE"
        ignore_issue = proposed_action == "IGNORE_TRANSIENT"

        description = issue.get(
            "description"
        ) or issue.get(
            "issue",
            "DQ issue detected"
        )

        # -------------------------------------------------
        # HIGH severity -> quarantine
        # -------------------------------------------------

        if ignore_issue:
            actions.append(
                {
                    "severity": severity,
                    "rule": rule,
                    "column": column,
                    "action": "MONITOR",
                    "agent_action": proposed_action,
                    "rows_affected": issue.get("count", 0),
                    "description": description,
                }
            )

        # The triage agent may authorize quarantine for a lower severity.
        elif severity == "HIGH" or force_quarantine:

            affected = pd.DataFrame()

            # Negative numeric values
            if rule == "PRICE_NON_NEGATIVE" and column in df.columns:

                mask = df[column] < 0
                affected = df.loc[mask].copy()

            # Invalid status values
            elif rule == "VALID_STATUS" and column in df.columns:

                valid_statuses = {
                    "PENDING",
                    "COMPLETED",
                    "CANCELLED",
                }

                mask = ~df[column].isin(valid_statuses)
                affected = df.loc[mask].copy()

            # Missing customer IDs
            elif rule == "NOT_NULL" and column in df.columns:

                mask = df[column].isna()
                affected = df.loc[mask].copy()

            if not affected.empty:

                quarantined_rows = pd.concat(
                    [
                        quarantined_rows,
                        affected
                    ],
                    ignore_index=True
                )

                actions.append(
                    {
                        "severity": severity,
                        "rule": rule,
                        "column": column,
                        "action": "QUARANTINE",
                        "agent_action": proposed_action or "SEVERITY_POLICY",
                        "rows_affected": len(affected),
                        "description": description,
                    }
                )

            else:

                actions.append(
                    {
                        "severity": severity,
                        "rule": rule,
                        "column": column,
                        "action": "NO_ACTION",
                        "agent_action": proposed_action or "SEVERITY_POLICY",
                        "rows_affected": 0,
                        "description": description,
                    }
                )

        # -------------------------------------------------
        # MEDIUM severity -> flag for review
        # -------------------------------------------------

        elif severity == "MEDIUM":

            actions.append(
                {
                    "severity": severity,
                    "rule": rule,
                    "column": column,
                    "action": "REVIEW",
                    "agent_action": proposed_action or "SEVERITY_POLICY",
                    "rows_affected": issue.get(
                        "count",
                        0
                    ),
                    "description": description,
                }
            )

        # -------------------------------------------------
        # LOW severity -> monitor
        # -------------------------------------------------

        else:

            actions.append(
                {
                    "severity": severity,
                    "rule": rule,
                    "column": column,
                    "action": "MONITOR",
                    "agent_action": proposed_action or "SEVERITY_POLICY",
                    "rows_affected": issue.get(
                        "count",
                        0
                    ),
                    "description": description,
                }
            )

    # -----------------------------------------------------
    # Save quarantine data
    # -----------------------------------------------------

    quarantine_path = None

    if not quarantined_rows.empty:

        QUARANTINE_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        quarantine_path = (
            QUARANTINE_DIR / "stg_orders_quarantine.parquet"
        )

        quarantined_rows.to_parquet(
            quarantine_path,
            index=False
        )

    # -----------------------------------------------------
    # Build result
    # -----------------------------------------------------

    result = {
        "input_file": str(input_path),
        "total_rows": len(df),
        "issues_received": len(issues),
        "actions": actions,
        "quarantined_rows": len(quarantined_rows),
        "quarantine_file": (
            str(quarantine_path)
            if quarantine_path
            else None
        ),
    }

    return result


# ---------------------------------------------------------
# Pretty printer
# ---------------------------------------------------------

def print_remediation_result(result: dict) -> None:
    """Print remediation results in a readable format."""

    print("\n=== REMEDIATION RESULT ===")

    print(
        "Input file:",
        result["input_file"]
    )

    print(
        "Total rows:",
        result["total_rows"]
    )

    print(
        "Issues received:",
        result["issues_received"]
    )

    print(
        "Quarantined rows:",
        result["quarantined_rows"]
    )

    if result["quarantine_file"]:

        print(
            "Quarantine file:",
            result["quarantine_file"]
        )

    print("\n--- Actions ---")

    if not result["actions"]:

        print("No remediation actions required.")

    else:

        for action in result["actions"]:

            print(
                f'{action["severity"]} | '
                f'{action["rule"]} | '
                f'{action["action"]} | '
                f'rows={action["rows_affected"]}'
            )


# ---------------------------------------------------------
# Standalone test
# ---------------------------------------------------------

if __name__ == "__main__":

    # Example issues matching the DQ detector
    sample_issues = [
        {
            "severity": "HIGH",
            "rule": "PRICE_NON_NEGATIVE",
            "column": "price",
            "count": 3,
            "description": "Negative prices detected",
        },
        {
            "severity": "MEDIUM",
            "rule": "NOT_NULL",
            "column": "customer_id",
            "count": 2,
            "description": "Missing customer IDs detected",
        },
        {
            "severity": "MEDIUM",
            "rule": "VALID_STATUS",
            "column": "status",
            "count": 2,
            "description": "Invalid status values detected",
        },
    ]

    result = remediate_dq_issues(
        INPUT_FILE,
        sample_issues
    )

    print_remediation_result(result)