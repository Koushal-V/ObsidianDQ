"""Durable, local incident memory for evidence-backed agent decisions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


MEMORY_FILE = Path(__file__).resolve().parents[3] / "data" / "memory" / "incident_memory.jsonl"


def save_incident_memory(record: dict[str, Any]) -> None:
    """Append a structured incident record without overwriting prior runs."""
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with MEMORY_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, default=str) + "\n")


def search_similar_incidents(column: str, rule: str, limit: int = 5) -> list[dict[str, Any]]:
    """Return recent matching incidents, newest first, from local durable memory."""
    if not MEMORY_FILE.exists():
        return []

    matches: list[dict[str, Any]] = []
    for line in MEMORY_FILE.read_text(encoding="utf-8").splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        issue_keys = record.get("issue_keys", [])
        if f"{rule}:{column}" in issue_keys or (
            column in record.get("failed_columns", []) and rule in record.get("failed_rules", [])
        ):
            matches.append(record)
    return list(reversed(matches[-limit:]))
