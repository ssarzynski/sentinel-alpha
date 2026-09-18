from sentinel_alpha.auth import AccountStatus, AccountStore
from sentinel_alpha.sessions import SessionStore

def test_active_session_metadata_never_exposes_token_hash(tmp_path):
    db=tmp_path/"sessions.db"
    accounts=AccountStore(db)
    accounts.create_user("member","member-long-passphrase",status=AccountStatus.ACTIVE)
    user=accounts.authenticate("member","member-long-passphrase")
    sessions=SessionStore(db)
    created=sessions.create(user)
    rows=sessions.active_sessions(user.user_id)
    assert len(rows)==1
    assert "token_hash" not in rows[0]
    assert "token" not in rows[0]
    assert rows[0]["mfa_verified"] == 0
    sessions.revoke_all(user.user_id)
    assert sessions.active_sessions(user.user_id)==[]
