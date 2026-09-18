"""Managed relational persistence foundation.

This module is intentionally infrastructure-only during consolidation. Existing
security/evidence stores remain authoritative until migrated behind regression
coverage; importing this module must not create or alter production tables.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    """Base for canonical managed models introduced by Alembic migrations."""


def database_url() -> str:
    return os.getenv("SENTINEL_DATABASE_URL", "sqlite:///sentinel_alpha.db")


def build_engine(url: str | None = None) -> Engine:
    engine = create_engine(url or database_url(), pool_pre_ping=True)
    if engine.dialect.name == "sqlite":
        @event.listens_for(engine, "connect")
        def _sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    return engine


def session_factory(engine: Engine):
    return sessionmaker(bind=engine, class_=Session, expire_on_commit=False)


def session_scope(engine: Engine) -> Iterator[Session]:
    """Yield a transaction-scoped session and roll back on any exception."""
    factory = session_factory(engine)
    session = factory()
    try:
        with session.begin():
            yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
