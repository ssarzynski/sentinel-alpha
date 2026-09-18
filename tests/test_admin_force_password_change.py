from sentinel_alpha.admin_accounts import AdminAccountService
from sentinel_alpha.auth import AccountStatus, AccountStore, Role
from sentinel_alpha.sessions import SessionStore

def test_admin_can_require_user_password_change_and_revoke_sessions(tmp_path):
    db=tmp_path/"auth.db"
    accounts=AccountStore(db)
    accounts.create_user("administrator","administrator-passphrase",role=Role.ADMIN,status=AccountStatus.ACTIVE)
    accounts.create_user("member","member-long-passphrase",status=AccountStatus.ACTIVE)
    admin=accounts.authenticate("administrator","administrator-passphrase")
    member=accounts.authenticate("member","member-long-passphrase")
    sessions=SessionStore(db)
    sessions.create(member)
    AdminAccountService(accounts,sessions).require_password_change(admin,member.user_id)
    with accounts._connect() as connection:
        row=connection.execute("SELECT must_change_password FROM users WHERE id=?",(member.user_id,)).fetchone()
    assert row["must_change_password"] == 1
    assert sessions.active_sessions(member.user_id) == []
