import sqlite3
import pytest
from sentinel_alpha.auth import AccountStatus, AccountStore, Role
from sentinel_alpha.mfa import AdminMfaStore
from sentinel_alpha.security_audit import SecurityAuditLog

def test_totp_secret_is_not_stored_in_plaintext(tmp_path):
    db=tmp_path/"mfa-encrypted.db"
    accounts=AccountStore(db)
    accounts.create_user("administrator","administrator-passphrase",role=Role.ADMIN,status=AccountStatus.ACTIVE)
    admin=accounts.authenticate("administrator","administrator-passphrase")
    enrollment=AdminMfaStore(db,SecurityAuditLog(db)).begin_enrollment(admin)
    with sqlite3.connect(db) as connection:
        stored=connection.execute("SELECT totp_secret FROM admin_mfa WHERE user_id=?",(admin.user_id,)).fetchone()[0]
    assert stored != enrollment.secret
    assert enrollment.secret not in stored

def test_mfa_store_fails_closed_without_encryption_key(tmp_path,monkeypatch):
    monkeypatch.delenv("SENTINEL_MFA_ENCRYPTION_KEY",raising=False)
    with pytest.raises(RuntimeError,match="required"):
        AdminMfaStore(tmp_path/"mfa.db",SecurityAuditLog(tmp_path/"mfa.db"))
