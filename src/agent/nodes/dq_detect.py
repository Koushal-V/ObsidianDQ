from pathlib import Path

import pandas as pd


ALLOWED_STATUSES = {"COMPLETED", "PENDING", "CANCELLED"}


def load_stage(stage_path: str) -> pd.DataFrame:
    """Load a CSV or Parquet stage."""
    path = Path(stage_path)

    if not path.exists():
        raise FileNotFoundError(f"Stage file not found: {path}")

    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)

    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)

    raise ValueError(
        f"Unsupported file format: {path.suffix}. "
        "Only CSV and Parquet are supported."
    )


def detect_dq_issues(stage_path: str) -> dict:
    """
    Run deterministic data-quality checks on a stage.
    """
    df = load_stage(stage_path)

    issues = []

    # -----------------------------------------------------
    # 1. Missing-value checks
    # -----------------------------------------------------

    for column in df.columns:
        null_count = int(df[column].isna().sum())

        if null_count > 0:
            issues.append(
                {
                    "rule": "NOT_NULL",
                    "column": column,
                    "issue": "Missing values detected",
                    "count": null_count,
                    "severity": "MEDIUM",
                }
            )

    # -----------------------------------------------------
    # 2. Duplicate-row check
    # -----------------------------------------------------

    duplicate_count = int(df.duplicated().sum())

    if duplicate_count > 0:
        issues.append(
            {
                "rule": "NO_DUPLICATES",
                "column": None,
                "issue": "Duplicate rows detected",
                "count": duplicate_count,
                "severity": "LOW",
            }
        )

    # -----------------------------------------------------
    # 3. Price validation
    # -----------------------------------------------------

    if "price" in df.columns:
        invalid_price_count = int((df["price"] < 0).sum())

        if invalid_price_count > 0:
            issues.append(
                {
                    "rule": "PRICE_NON_NEGATIVE",
                    "column": "price",
                    "issue": "Negative prices detected",
                    "count": invalid_price_count,
                    "severity": "HIGH",
                }
            )

    # -----------------------------------------------------
    # 4. Status validation
    # -----------------------------------------------------

    if "status" in df.columns:
        invalid_status_count = int(
            (~df["status"].isin(ALLOWED_STATUSES)).sum()
        )

        if invalid_status_count > 0:
            issues.append(
                {
                    "rule": "VALID_STATUS",
                    "column": "status",
                    "issue": "Invalid status values detected",
                    "count": invalid_status_count,
                    "severity": "MEDIUM",
                }
            )

    # -----------------------------------------------------
    # 5. Order ID uniqueness
    # -----------------------------------------------------

    if "order_id" in df.columns:
        duplicate_order_ids = int(
            df["order_id"].duplicated().sum()
        )

        if duplicate_order_ids > 0:
            issues.append(
                {
                    "rule": "UNIQUE_ORDER_ID",
                    "column": "order_id",
                    "issue": "Duplicate order IDs detected",
                    "count": duplicate_order_ids,
                    "severity": "HIGH",
                }
            )

    # -----------------------------------------------------
    # Summary
    # -----------------------------------------------------

    high_count = sum(
        1 for issue in issues if issue["severity"] == "HIGH"
    )

    medium_count = sum(
        1 for issue in issues if issue["severity"] == "MEDIUM"
    )

    low_count = sum(
        1 for issue in issues if issue["severity"] == "LOW"
    )

    return {
        "stage_path": str(stage_path),
        "row_count": int(len(df)),
        "issue_count": len(issues),
        "severity_summary": {
            "HIGH": high_count,
            "MEDIUM": medium_count,
            "LOW": low_count,
        },
        "issues": issues,
    }


if __name__ == "__main__":
    result = detect_dq_issues(
        "data/raw/stg_orders.parquet"
    )

    print("=== DQ DETECTION RESULT ===")
    print("Rows:", result["row_count"])
    print("Issues:", result["issue_count"])
    print("Severity:", result["severity_summary"])

    print("\n--- Detected Issues ---")

    for issue in result["issues"]:
        print(
            f"{issue['severity']} | "
            f"{issue['rule']} | "
            f"{issue['column']} | "
            f"{issue['issue']} | "
            f"count={issue['count']}"
        )