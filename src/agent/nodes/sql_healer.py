"""
ObsidianDQ - SQL Healer
-----------------------

AST-grounded SQL validation and self-healing using sqlglot.

This module is intentionally independent from graph.py and state.py
to avoid circular imports.

Main function used by graph.py:

    heal_sql(
        sql_file="data/queries/fct_sales.sql",
        input_file="data/raw/stg_orders.parquet"
    )

The healer:
1. Loads the original SQL.
2. Parses SQL using sqlglot.
3. Detects structural SQL problems.
4. Normalizes the SQL AST.
5. Validates referenced tables against available project data.
6. Produces repaired SQL when possible.
7. Writes the repaired SQL to disk.
8. Returns a deterministic result dictionary.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
import re

import sqlglot
from sqlglot import exp


# ============================================================
# PROJECT PATHS
# ============================================================

# sql_healer.py:
# ObsidianDQ/src/agent/nodes/sql_healer.py
#
# parents[0] -> nodes
# parents[1] -> agent
# parents[2] -> src
# parents[3] -> ObsidianDQ
#
# Therefore parents[3] is the project root.

PROJECT_ROOT = Path(__file__).resolve().parents[3]

DATA_DIR = PROJECT_ROOT / "data"
QUERY_DIR = DATA_DIR / "queries"
HEALED_DIR = QUERY_DIR / "healed"

HEALED_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# SQL LOADING
# ============================================================

def load_sql(sql_path: str | Path) -> str:
    """
    Load SQL text from a file.
    """

    path = Path(sql_path)

    if not path.is_absolute():
        path = PROJECT_ROOT / path

    if not path.exists():
        raise FileNotFoundError(f"SQL file not found: {path}")

    return path.read_text(encoding="utf-8").strip()


# ============================================================
# SQL SAVING
# ============================================================

def save_sql(
    sql: str,
    output_path: str | Path,
) -> str:
    """
    Save SQL text to a file and return the absolute path.
    """

    path = Path(output_path)

    if not path.is_absolute():
        path = PROJECT_ROOT / path

    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text(
        sql.rstrip() + "\n",
        encoding="utf-8",
    )

    return str(path)


# ============================================================
# SQL PARSING
# ============================================================

def parse_sql(sql: str) -> exp.Expression:
    """
    Parse SQL into a sqlglot AST.

    DuckDB is used as the target SQL dialect.
    """

    if not sql or not sql.strip():
        raise ValueError("SQL input is empty.")

    statements = sqlglot.parse(
        sql,
        read="duckdb",
    )

    if not statements:
        raise ValueError("No SQL statement could be parsed.")

    if len(statements) > 1:
        # The project currently expects one transformation query.
        return statements[0]

    return statements[0]


# ============================================================
# TABLE EXTRACTION
# ============================================================

def extract_tables(sql: str) -> List[str]:
    """
    Extract table references from SQL.
    """

    try:
        tree = parse_sql(sql)
    except Exception:
        return []

    tables = []

    for table in tree.find_all(exp.Table):
        name = table.name

        if name and name not in tables:
            tables.append(name)

    return sorted(tables)


# ============================================================
# COLUMN EXTRACTION
# ============================================================

def extract_columns(sql: str) -> List[str]:
    """
    Extract column references from SQL.
    """

    try:
        tree = parse_sql(sql)
    except Exception:
        return []

    columns = []

    for column in tree.find_all(exp.Column):
        name = column.name

        if name and name not in columns:
            columns.append(name)

    return sorted(columns)


# ============================================================
# SQL PROBLEM DETECTION
# ============================================================

def detect_sql_problems(sql: str) -> List[Dict[str, Any]]:
    """
    Detect deterministic SQL problems.

    This function does not modify SQL.
    """

    problems: List[Dict[str, Any]] = []

    if not sql or not sql.strip():
        problems.append(
            {
                "type": "EMPTY_SQL",
                "message": "SQL query is empty.",
            }
        )
        return problems

    # --------------------------------------------------------
    # Parse validation
    # --------------------------------------------------------

    try:
        tree = parse_sql(sql)
    except Exception as exc:
        problems.append(
            {
                "type": "SQL_PARSE_ERROR",
                "message": str(exc),
            }
        )
        return problems

    # --------------------------------------------------------
    # SELECT * detection
    # --------------------------------------------------------

    for star in tree.find_all(exp.Star):
        problems.append(
            {
                "type": "SELECT_STAR",
                "message": "SELECT * detected.",
            }
        )
        break

    # --------------------------------------------------------
    # Missing semicolon
    # --------------------------------------------------------

    if sql.strip() and not sql.strip().endswith(";"):
        problems.append(
            {
                "type": "MISSING_SEMICOLON",
                "message": "SQL statement does not end with a semicolon.",
            }
        )

    # --------------------------------------------------------
    # Suspicious comma
    # --------------------------------------------------------

    if re.search(
        r",\s*(FROM|WHERE|GROUP\s+BY|ORDER\s+BY|JOIN)\b",
        sql,
        re.I,
    ):
        problems.append(
            {
                "type": "TRAILING_COMMA",
                "message": "Possible trailing comma detected.",
            }
        )

    # --------------------------------------------------------
    # SELECT without FROM
    # --------------------------------------------------------

    if isinstance(tree, exp.Select):
        if not tree.args.get("from") and not tree.args.get("from_"):
            problems.append(
                {
                    "type": "SELECT_WITHOUT_FROM",
                    "message": "SELECT statement has no FROM clause.",
                }
            )

    return problems


# ============================================================
# AST NORMALIZATION
# ============================================================

def normalize_sql_ast(sql: str) -> str:
    """
    Parse SQL and regenerate it from the AST.

    This provides deterministic AST normalization.
    """

    tree = parse_sql(sql)

    normalized = tree.sql(
        dialect="duckdb",
        pretty=True,
    )

    return normalized.strip()


# ============================================================
# BASIC AST REPAIR
# ============================================================

def repair_sql_ast(
    sql: str,
) -> Dict[str, Any]:
    """
    Repair SQL deterministically using sqlglot.

    The repair strategy intentionally avoids hallucinating
    columns or tables.

    Safe repairs include:
    - SQL AST normalization
    - formatting
    - removing unnecessary trailing semicolon duplication
    - ensuring one final semicolon
    """

    original_sql = sql

    problems = detect_sql_problems(sql)

    if any(
        problem["type"] == "SQL_PARSE_ERROR"
        for problem in problems
    ):
        return {
            "original_sql": original_sql,
            "repaired_sql": original_sql,
            "problems": problems,
            "repairs": [],
            "changed": False,
            "success": False,
        }

    try:
        repaired_sql = normalize_sql_ast(sql)

        # ----------------------------------------------------
        # Normalize semicolon
        # ----------------------------------------------------

        repaired_sql = repaired_sql.rstrip(";").rstrip()
        repaired_sql += ";"

        repairs: List[Dict[str, Any]] = []

        if repaired_sql.strip() != original_sql.strip():
            repairs.append(
                {
                    "type": "AST_NORMALIZATION",
                    "description": (
                        "SQL was parsed and regenerated from "
                        "the sqlglot AST."
                    ),
                    "old": original_sql,
                    "new": repaired_sql,
                }
            )

        return {
            "original_sql": original_sql,
            "repaired_sql": repaired_sql,
            "problems": problems,
            "repairs": repairs,
            "changed": repaired_sql.strip() != original_sql.strip(),
            "success": True,
        }

    except Exception as exc:
        return {
            "original_sql": original_sql,
            "repaired_sql": original_sql,
            "problems": problems,
            "repairs": [],
            "changed": False,
            "success": False,
            "error": str(exc),
        }


# ============================================================
# INPUT FILE DISCOVERY
# ============================================================

def discover_available_tables(
    input_file: Optional[str] = None,
) -> List[str]:
    """
    Discover tables represented by project data files.

    This does not create a database connection. It only maps
    physical data files to logical table names.
    """

    tables: List[str] = []

    # --------------------------------------------------------
    # Explicit input file
    # --------------------------------------------------------

    if input_file:
        path = Path(input_file)

        if not path.is_absolute():
            path = PROJECT_ROOT / path

        if path.exists():
            tables.append(path.stem)

    # --------------------------------------------------------
    # Project data directories
    # --------------------------------------------------------

    search_dirs = [
        DATA_DIR,
        DATA_DIR / "raw",
        DATA_DIR / "staging",
        DATA_DIR / "queries",
    ]

    for directory in search_dirs:

        if not directory.exists():
            continue

        for path in directory.rglob("*"):

            if not path.is_file():
                continue

            if path.suffix.lower() not in {
                ".csv",
                ".parquet",
                ".json",
                ".db",
            }:
                continue

            name = path.stem

            if name not in tables:
                tables.append(name)

    return sorted(tables)


# ============================================================
# TABLE VALIDATION
# ============================================================

def validate_table_references(
    sql: str,
    input_file: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Compare SQL table references with available project data.

    This is advisory rather than destructive.
    """

    referenced_tables = extract_tables(sql)

    available_tables = discover_available_tables(
        input_file=input_file,
    )

    missing_tables = []

    normalized_available = {
        table.lower()
        for table in available_tables
    }

    for table in referenced_tables:

        if table.lower() not in normalized_available:

            # SQL may reference a table generated by a previous
            # transformation. Therefore this is only a warning.
            missing_tables.append(table)

    return {
        "referenced_tables": referenced_tables,
        "available_tables": available_tables,
        "missing_tables": sorted(missing_tables),
    }


# ============================================================
# SQL DIFF
# ============================================================

def build_sql_diff(
    old_sql: str,
    new_sql: str,
) -> Dict[str, Any]:
    """
    Build a compact deterministic SQL diff.
    """

    old_lines = old_sql.strip().splitlines()
    new_lines = new_sql.strip().splitlines()

    removed = [
        line
        for line in old_lines
        if line not in new_lines
    ]

    added = [
        line
        for line in new_lines
        if line not in old_lines
    ]

    return {
        "changed": old_sql.strip() != new_sql.strip(),
        "removed": removed,
        "added": added,
    }


# ============================================================
# MAIN SQL HEALER
# ============================================================

def heal_sql(
    sql_path: str | Path | None = None,
    output_path: str | Path | None = None,
    sql_file: str | Path | None = None,
    input_file: str | Path | None = None,
) -> Dict[str, Any]:
    """
    Main SQL healing function.

    Compatible with graph.py calls such as:

        heal_sql(
            sql_file=state["sql_file"],
            input_file=state["input_file"],
        )

    Also supports:

        heal_sql(
            sql_path="data/queries/fct_sales.sql"
        )

    Parameters
    ----------
    sql_path:
        SQL file path.

    output_path:
        Destination for healed SQL.

    sql_file:
        Alias for sql_path. Used by graph.py.

    input_file:
        Input dataset used for table/schema awareness.
    """

    # --------------------------------------------------------
    # Resolve SQL input
    # --------------------------------------------------------

    if sql_file is not None:
        sql_path = sql_file

    if sql_path is None:
        raise ValueError(
            "SQL file path is required. "
            "Use sql_path= or sql_file=."
        )

    # --------------------------------------------------------
    # Resolve input file
    # --------------------------------------------------------

    resolved_input_file: Optional[str] = None

    if input_file is not None:
        input_path = Path(input_file)

        if not input_path.is_absolute():
            input_path = PROJECT_ROOT / input_path

        resolved_input_file = str(input_path)

    # --------------------------------------------------------
    # Load SQL
    # --------------------------------------------------------

    original_sql = load_sql(sql_path)

    # --------------------------------------------------------
    # Detect SQL problems
    # --------------------------------------------------------

    problems = detect_sql_problems(original_sql)

    # --------------------------------------------------------
    # AST repair
    # --------------------------------------------------------

    repair_result = repair_sql_ast(
        original_sql,
    )

    repaired_sql = repair_result["repaired_sql"]

    # --------------------------------------------------------
    # Table validation
    # --------------------------------------------------------

    table_validation = validate_table_references(
        repaired_sql,
        input_file=resolved_input_file,
    )

    # --------------------------------------------------------
    # SQL diff
    # --------------------------------------------------------

    diff = build_sql_diff(
        original_sql,
        repaired_sql,
    )

    # --------------------------------------------------------
    # Output file
    # --------------------------------------------------------

    if output_path is None:

        source_path = Path(sql_path)

        if not source_path.is_absolute():
            source_path = PROJECT_ROOT / source_path

        output_path = (
            HEALED_DIR
            / f"{source_path.stem}_healed.sql"
        )

    saved_path = save_sql(
        repaired_sql,
        output_path,
    )

    # --------------------------------------------------------
    # Final result
    # --------------------------------------------------------

    result = {
        "success": repair_result.get(
            "success",
            False,
        ),
        "original_sql": original_sql,
        "repaired_sql": repaired_sql,
        "sql_changed": diff["changed"],
        "repair_count": len(
            repair_result.get(
                "repairs",
                [],
            )
        ),
        "problems": problems,
        "repairs": repair_result.get(
            "repairs",
            [],
        ),
        "sql_diff": diff,
        "referenced_tables": table_validation[
            "referenced_tables"
        ],
        "available_tables": table_validation[
            "available_tables"
        ],
        "missing_tables": table_validation[
            "missing_tables"
        ],
        "output_file": saved_path,
        "input_file": resolved_input_file,
        "sql_file": str(sql_path),
    }

    if "error" in repair_result:
        result["error"] = repair_result["error"]

    return result


# ============================================================
# DISPLAY RESULT
# ============================================================

def print_healing_result(
    result: Dict[str, Any],
) -> None:
    """
    Pretty-print SQL healing results.
    """

    print()
    print("=" * 70)
    print("OBSIDIAN DQ - SQL HEALER")
    print("=" * 70)

    print(
        f"Success: {result.get('success', False)}"
    )

    print(
        f"SQL changed: {result.get('sql_changed', False)}"
    )

    print(
        f"Repair count: {result.get('repair_count', 0)}"
    )

    print()
    print("Referenced tables:")

    for table in result.get(
        "referenced_tables",
        [],
    ):
        print(f"- {table}")

    print()
    print("Detected SQL Problems:")

    problems = result.get(
        "problems",
        [],
    )

    if not problems:
        print("None")
    else:
        for problem in problems:
            print(
                f"- {problem.get('type')}: "
                f"{problem.get('message')}"
            )

    print()
    print("Repairs:")

    repairs = result.get(
        "repairs",
        [],
    )

    if not repairs:
        print("None")
    else:
        for repair in repairs:
            print(
                f"- {repair.get('type')}: "
                f"{repair.get('description')}"
            )

    print()
    print("Repaired SQL:")
    print("-" * 70)
    print(
        result.get(
            "repaired_sql",
            "",
        )
    )

    print()
    print(
        "Output file:",
        result.get(
            "output_file",
            "",
        ),
    )

    print("=" * 70)


# ============================================================
# STANDALONE TEST
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 70)
    print("SQL HEALER STANDALONE TEST")
    print("=" * 70)

    # --------------------------------------------------------
    # Try the project's Phase 1 SQL file.
    # --------------------------------------------------------

    default_sql = DATA_DIR / "queries" / "fct_sales.sql"

    if not default_sql.exists():

        print()
        print(
            "SQL file not found:",
            default_sql,
        )

        print()
        print(
            "Create the Phase 1 SQL file first, "
            "or call heal_sql() from graph.py."
        )

    else:

        result = heal_sql(
            sql_file=str(default_sql),
            input_file=str(
                DATA_DIR
                / "raw"
                / "stg_orders.parquet"
            ),
        )

        print_healing_result(result)