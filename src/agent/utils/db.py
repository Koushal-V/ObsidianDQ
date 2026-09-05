"""
ObsidianDQ - DuckDB Utility Helper
------------------------------------
Provides in-memory DuckDB connection management and DataFrame query capabilities.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd

try:
    import duckdb
    DUCKDB_AVAILABLE = True
except ImportError:
    duckdb = None
    DUCKDB_AVAILABLE = False


def execute_duckdb_query(query: str, tables: Optional[Dict[str, pd.DataFrame]] = None) -> pd.DataFrame:
    """
    Execute a DuckDB SQL query against in-memory DataFrames or persistent files.
    """
    if not DUCKDB_AVAILABLE:
        raise RuntimeError("DuckDB is not installed in the current environment.")

    con = duckdb.connect(database=":memory:")
    
    if tables:
        for table_name, df in tables.items():
            con.register(table_name, df)

    result = con.execute(query).df()
    con.close()
    return result


def query_file(file_path: str | Path, query: Optional[str] = None) -> pd.DataFrame:
    """
    Register a CSV or Parquet file into an in-memory DuckDB table and run a query.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    ext = path.suffix.lower()
    table_name = path.stem

    if ext == ".csv":
        df = pd.read_csv(path)
    elif ext == ".parquet":
        df = pd.read_parquet(path)
    else:
        raise ValueError(f"Unsupported file extension: {ext}")

    if not query:
        query = f"SELECT * FROM {table_name}"

    return execute_duckdb_query(query, {table_name: df})
