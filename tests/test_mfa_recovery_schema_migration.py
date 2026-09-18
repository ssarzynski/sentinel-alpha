import sqlite3
from sentinel_alpha.browser_auth import _ensure_recovery_attempt_schema

def test_legacy_recovery_attempt_schema_migrates_account_wide(tmp_path):
    db = tmp_path / "legacy.db"
    connection = sqlite3.connect(db)
    connection.row_factory = sqlite3.Row
    connection.execute("""CREATE TABLE mfa_recovery_attempts (
        user_id INTEGER NOT NULL, session_fingerprint TEXT NOT NULL,
        source_fingerprint TEXT NOT NULL, failures INTEGER NOT NULL DEFAULT 0,
        blocked_until TEXT, PRIMARY KEY(user_id,session_fingerprint,source_fingerprint)
    )""")
    connection.execute("INSERT INTO mfa_recovery_attempts VALUES(?,?,?,?,?)",
                       (7,"session-a","source-a",2,None))
    connection.execute("INSERT INTO mfa_recovery_attempts VALUES(?,?,?,?,?)",
                       (7,"session-b","source-b",3,"2099-01-01T00:00:00+00:00"))
    _ensure_recovery_attempt_schema(connection)
    info = connection.execute("PRAGMA table_info(mfa_recovery_attempts)").fetchall()
    assert [r["name"] for r in info if r["pk"]] == ["user_id"]
    row = connection.execute("SELECT * FROM mfa_recovery_attempts WHERE user_id=7").fetchone()
    assert row["failures"] == 5
    assert row["blocked_until"] == "2099-01-01T00:00:00+00:00"
    connection.execute("""INSERT INTO mfa_recovery_attempts
        (user_id,session_fingerprint,source_fingerprint,failures,blocked_until)
        VALUES(?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET failures=excluded.failures""",
        (7,"new","new",6,None))
    assert connection.execute("SELECT failures FROM mfa_recovery_attempts WHERE user_id=7").fetchone()["failures"] == 6
    _ensure_recovery_attempt_schema(connection)
    connection.close()
