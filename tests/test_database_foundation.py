import sqlite3

import pytest
from sqlalchemy import text

from sentinel_alpha.database import Base, build_engine, session_scope


def test_import_and_engine_creation_do_not_create_application_tables(tmp_path):
    database=tmp_path/"foundation.db"
    engine=build_engine(f"sqlite:///{database}")
    with engine.connect() as connection:
        tables=connection.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).scalars().all()
    assert tables==[]
    assert list(Base.metadata.tables)==[]
    engine.dispose()


def test_sqlite_engine_enforces_foreign_keys(tmp_path):
    engine=build_engine(f"sqlite:///{tmp_path/'fk.db'}")
    with engine.connect() as connection:
        assert connection.execute(text("PRAGMA foreign_keys")).scalar_one()==1
    engine.dispose()


def test_session_scope_commits_and_rolls_back(tmp_path):
    path=tmp_path/"transactions.db"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE values_test(id INTEGER PRIMARY KEY, value TEXT NOT NULL)")
    engine=build_engine(f"sqlite:///{path}")
    with session_scope(engine) as session:
        session.execute(text("INSERT INTO values_test(value) VALUES ('kept')"))
    with pytest.raises(RuntimeError):
        with session_scope(engine) as session:
            session.execute(text("INSERT INTO values_test(value) VALUES ('rolled-back')"))
            raise RuntimeError("stop")
    with engine.connect() as connection:
        values=connection.execute(text("SELECT value FROM values_test ORDER BY id")).scalars().all()
    assert values==["kept"]
    engine.dispose()
