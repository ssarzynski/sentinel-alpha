import sqlite3

import pytest

from sentinel_alpha.auth import AccountStatus, AccountStore, Role, require_admin


def test_new_user_defaults_pending_and_cannot_authenticate(tmp_path):
    store = AccountStore(tmp_path / "auth.db")
    store.create_user("new.user", "long-test-passphrase")
    assert store.authenticate("new.user", "long-test-passphrase") is None


def test_active_user_authenticates_with_generic_failure_behavior(tmp_path):
    store = AccountStore(tmp_path / "auth.db")
    store.create_user("member", "long-test-passphrase", status=AccountStatus.ACTIVE)
    assert store.authenticate("member", "wrong-password-value") is None
    assert store.authenticate("unknown", "wrong-password-value") is None
    assert store.authenticate("member", "long-test-passphrase") is not None


def test_user_cannot_pass_admin_authorization(tmp_path):
    store = AccountStore(tmp_path / "auth.db")
    store.create_user("member", "long-test-passphrase", status=AccountStatus.ACTIVE)
    account = store.authenticate("member", "long-test-passphrase")
    assert account is not None
    with pytest.raises(PermissionError):
        require_admin(account)


def test_admin_authorization_requires_active_admin(tmp_path):
    store = AccountStore(tmp_path / "auth.db")
    store.create_user(
        "administrator", "long-test-passphrase",
        role=Role.ADMIN, status=AccountStatus.ACTIVE, must_change_password=True,
    )
    account = store.authenticate("administrator", "long-test-passphrase")
    assert account is not None
    require_admin(account)


def test_username_is_case_normalized_and_unique(tmp_path):
    store = AccountStore(tmp_path / "auth.db")
    store.create_user("Member", "long-test-passphrase")
    with pytest.raises(sqlite3.IntegrityError):
        store.create_user("member", "another-long-passphrase")
