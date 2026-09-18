import pyotp

from sentinel_alpha.auth import AccountStatus, AccountStore, Role
from sentinel_alpha.mfa import AdminMfaStore
from sentinel_alpha.security_audit import SecurityAuditLog


def test_admin_mfa_enrollment_and_verification(tmp_path):
    db = tmp_path / "mfa.db"
    accounts = AccountStore(db)
    accounts.create_user(
        "administrator", "administrator-passphrase",
        role=Role.ADMIN, status=AccountStatus.ACTIVE,
    )
    admin = accounts.authenticate("administrator", "administrator-passphrase")
    assert admin is not None
    audit = SecurityAuditLog(db)
    mfa = AdminMfaStore(db, audit)
    enrollment = mfa.begin_enrollment(admin)
    code = pyotp.TOTP(enrollment.secret).now()
    assert mfa.confirm_enrollment(admin, code) is True
    assert mfa.enabled(admin) is True
    assert mfa.verify(admin, pyotp.TOTP(enrollment.secret).now()) is True
    assert audit.verify_integrity() is True


def test_admin_without_enrollment_fails_mfa(tmp_path):
    db = tmp_path / "mfa.db"
    accounts = AccountStore(db)
    accounts.create_user(
        "administrator", "administrator-passphrase",
        role=Role.ADMIN, status=AccountStatus.ACTIVE,
    )
    admin = accounts.authenticate("administrator", "administrator-passphrase")
    assert admin is not None
    mfa = AdminMfaStore(db, SecurityAuditLog(db))
    assert mfa.verify(admin, "000000") is False


def test_normal_user_does_not_require_admin_mfa(tmp_path):
    db = tmp_path / "mfa.db"
    accounts = AccountStore(db)
    accounts.create_user("member", "member-test-passphrase", status=AccountStatus.ACTIVE)
    member = accounts.authenticate("member", "member-test-passphrase")
    assert member is not None
    mfa = AdminMfaStore(db, SecurityAuditLog(db))
    assert mfa.verify(member, "") is True
