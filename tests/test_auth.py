import sqlite3

import pytest

from sentinel_alpha.auth import (
    AccountStatus,
    AccountStore,
    Role,
    provision_bootstrap_admin,
    require_admin,
)


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



def test_password_hash_uses_argon2id(tmp_path):
    store = AccountStore(tmp_path / "auth.db")
    store.create_user("member", "long-test-passphrase")
    with store._connect() as connection:
        encoded = connection.execute(
            "SELECT password_hash FROM users WHERE username='member'"
        ).fetchone()[0]
    assert encoded.startswith("$argon2id$")
    assert "long-test-passphrase" not in encoded


def test_bootstrap_admin_requires_environment_secret(monkeypatch, tmp_path):
    store = AccountStore(tmp_path / "auth.db")
    monkeypatch.delenv("SENTINEL_BOOTSTRAP_ADMIN_USERNAME", raising=False)
    monkeypatch.delenv("SENTINEL_BOOTSTRAP_ADMIN_PASSWORD", raising=False)
    assert provision_bootstrap_admin(store) is None


def test_bootstrap_admin_is_active_but_requires_password_change(monkeypatch, tmp_path):
    store = AccountStore(tmp_path / "auth.db")
    monkeypatch.setenv("SENTINEL_BOOTSTRAP_ADMIN_USERNAME", "bootstrap-admin")
    monkeypatch.setenv("SENTINEL_BOOTSTRAP_ADMIN_PASSWORD", "temporary-test-passphrase")
    user_id = provision_bootstrap_admin(store)
    assert user_id is not None
    account = store.authenticate("bootstrap-admin", "temporary-test-passphrase")
    assert account is not None
    assert account.role is Role.ADMIN
    assert account.must_change_password is True
    assert provision_bootstrap_admin(store) is None
