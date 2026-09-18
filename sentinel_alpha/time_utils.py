"""Shared datetime boundary helpers."""
from __future__ import annotations

from datetime import datetime, timezone


def as_utc(value: datetime | None) -> datetime | None:
    """Return an aware UTC datetime.

    Sentinel persists timestamps as UTC. Some database drivers, notably SQLite,
    may return a naive value for timezone-aware columns; those values are
    therefore interpreted as UTC at the application boundary.
    """
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
