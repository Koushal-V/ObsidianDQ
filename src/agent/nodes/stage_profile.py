from pathlib import Path

import pandas as pd


def load_stage(stage_path: str) -> pd.DataFrame:
    """
    Load a CSV or Parquet stage into a pandas DataFrame.
    """
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


def profile_stage(stage_path: str) -> dict:
    """
    Create a deterministic profile of a data stage.
    """
    df = load_stage(stage_path)

    profile = {
        "stage_path": str(stage_path),
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
        "columns": {},
    }

    for column in df.columns:
        series = df[column]

        column_profile = {
            "dtype": str(series.dtype),
            "null_count": int(series.isna().sum()),
            "null_percentage": round(
                float(series.isna().mean() * 100), 2
            ),
            "unique_count": int(series.nunique(dropna=True)),
        }

        # Numeric statistics
        if pd.api.types.is_numeric_dtype(series):
            column_profile["statistics"] = {
                "min": float(series.min())
                if not series.dropna().empty
                else None,
                "max": float(series.max())
                if not series.dropna().empty
                else None,
                "mean": float(series.mean())
                if not series.dropna().empty
                else None,
                "median": float(series.median())
                if not series.dropna().empty
                else None,
            }

        # Most frequent values
        value_counts = series.value_counts(dropna=False).head(5)

        column_profile["top_values"] = {
            str(value): int(count)
            for value, count in value_counts.items()
        }

        profile["columns"][column] = column_profile

    return profile
if __name__ == "__main__":
    profile = profile_stage("data/raw/stg_orders.parquet")

    print("=== STAGE PROFILE ===")
    print("Rows:", profile["row_count"])
    print("Columns:", profile["column_count"])

    for column, details in profile["columns"].items():
        print(f"\n--- {column} ---")
        print("Data type:", details["dtype"])
        print("Null count:", details["null_count"])
        print("Null %:", details["null_percentage"])
        print("Unique values:", details["unique_count"])

        if "statistics" in details:
            print("Statistics:", details["statistics"])

        print("Top values:", details["top_values"])