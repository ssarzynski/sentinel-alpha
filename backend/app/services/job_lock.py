from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import text
from sqlalchemy.orm import Session


def _lock_id(name: str) -> int:
    # Stable signed 63-bit integer suitable for PostgreSQL advisory locks.
    value = 1469598103934665603
    for byte in name.encode("utf-8"):
        value ^= byte
        value *= 1099511628211
        value &= (1 << 63) - 1
    return value


@contextmanager
def advisory_job_lock(db: Session, name: str) -> Iterator[bool]:
    if not name.strip():
        raise ValueError("lock name is required")
    lock_id = _lock_id(name)
    acquired = bool(db.scalar(text("SELECT pg_try_advisory_lock(:lock_id)"), {"lock_id": lock_id}))
    try:
        yield acquired
    finally:
        if acquired:
            db.scalar(text("SELECT pg_advisory_unlock(:lock_id)"), {"lock_id": lock_id})
