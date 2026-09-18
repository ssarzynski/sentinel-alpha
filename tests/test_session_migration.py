import sqlite3
from sentinel_alpha.auth import AccountStore
from sentinel_alpha.sessions import SessionStore

def test_existing_session_table_gets_mfa_column(tmp_path):
    db=tmp_path/"old.db"
    AccountStore(db)
    with sqlite3.connect(db) as connection:
        connection.execute("""CREATE TABLE auth_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token_hash TEXT NOT NULL UNIQUE,
            user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            revoked_at TEXT,
            restricted_to_password_change INTEGER NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )""")
    SessionStore(db)
    with sqlite3.connect(db) as connection:
        columns={row[1] for row in connection.execute("PRAGMA table_info(auth_sessions)")}
    assert "mfa_verified" in columns
