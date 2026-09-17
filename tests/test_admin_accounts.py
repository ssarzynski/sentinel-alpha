import pytest

from sentinel_alpha.admin_accounts import AdminAccountService
from sentinel_alpha.auth import AccountStatus, AccountStore, Role
from sentinel_alpha.sessions import SessionStore


def setup_accounts(tmp_path):
    db = tmp_path / "auth.db"
    accounts = AccountStore(db)
    admin_id = accounts.create_user(
        "administrator", "administrator-passphrase",
        role=Role.ADMIN, status=AccountStatus.ACTIVE,
    )
    admin = accounts.authenticate("administrator", "administrator-passphrase")
    assert admin is not None
    sessions = SessionStore(db)
    return accounts, sessions, AdminAccountService(accounts, sessions), admin, admin_id


def test_admin_can_approve_pending_account(tmp_path):
    accounts, sessions, service, admin, _ = setup_accounts(tmp_path)
    user_id = accounts.create_user("member", "member-test-passphrase")
    assert accounts.authenticate("member", "member-test-passphrase") is None
    service.approve(admin, user_id)
    assert accounts.authenticate("member", "member-test-passphrase") is not None


def test_ordinary_user_cannot_call_admin_service(tmp_path):
    accounts, sessions, service, admin, _ = setup_accounts(tmp_path)
    user_id = accounts.create_user(
        "member", "member-test-passphrase", status=AccountStatus.ACTIVE
    )
    user = accounts.authenticate("member", "member-test-passphrase")
    assert user is not None
    target_id = accounts.create_user("pending", "pending-test-passphrase")
    with pytest.raises(PermissionError):
        service.approve(user, target_id)


def test_rejection_keeps_account_out(tmp_path):
    accounts, sessions, service, admin, _ = setup_accounts(tmp_path)
    user_id = accounts.create_user("pending", "pending-test-passphrase")
    service.reject(admin, user_id)
    assert accounts.authenticate("pending", "pending-test-passphrase") is None


def test_disable_revokes_existing_sessions(tmp_path):
    accounts, sessions, service, admin, _ = setup_accounts(tmp_path)
    user_id = accounts.create_user(
        "member", "member-test-passphrase", status=AccountStatus.ACTIVE
    )
    user = accounts.authenticate("member", "member-test-passphrase")
    assert user is not None
    session = sessions.create(user)
    service.set_status(admin, user_id, AccountStatus.DISABLED)
    assert sessions.validate(session.token) is None


def test_role_change_revokes_sessions_and_user_cannot_self_promote(tmp_path):
    accounts, sessions, service, admin, _ = setup_accounts(tmp_path)
    user_id = accounts.create_user(
        "member", "member-test-passphrase", status=AccountStatus.ACTIVE
    )
    user = accounts.authenticate("member", "member-test-passphrase")
    assert user is not None
    session = sessions.create(user)
    with pytest.raises(PermissionError):
        service.set_role(user, user_id, Role.ADMIN)
    service.set_role(admin, user_id, Role.ADMIN)
    assert sessions.validate(session.token) is None


def test_admin_cannot_disable_or_demote_self(tmp_path):
    accounts, sessions, service, admin, admin_id = setup_accounts(tmp_path)
    with pytest.raises(ValueError):
        service.set_status(admin, admin_id, AccountStatus.DISABLED)
    with pytest.raises(ValueError):
        service.set_role(admin, admin_id, Role.USER)
