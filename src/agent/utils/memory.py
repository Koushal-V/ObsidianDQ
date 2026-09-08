"""Durable, local incident memory for evidence-backed agent decisions.

Backed by DuckDB (see src/agent/utils/db.py). The public functions
save_incident_memory() and search_similar_incidents() keep the same
signatures as the previous JSONL implementation so callers are unaffected.
"""

from __future__ import annotations

from typing import Any

from .db import save_incident_memory as _db_save_incident_memory
from .db import search_similar_incidents as _db_search_similar_incidents


def save_incident_memory(record: dict[str, Any]) -> None:
    """Append a structured incident record without overwriting prior runs."""
    _db_save_incident_memory(record)


def search_similar_incidents(column: str, rule: str, limit: int = 5) -> list[dict[str, Any]]:
    """Return recent matching incidents, newest first, from local durable memory."""
    return _db_search_similar_incidents(column, rule, limit)

