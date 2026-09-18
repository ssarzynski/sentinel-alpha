import hashlib
from sentinel_alpha.auth import AccountStatus, AccountStore, Role
from sentinel_alpha.mfa import AdminMfaStore
from sentinel_alpha.security_audit import SecurityAuditLog

def test_recovery_codes_are_hashed_and_single_use(tmp_path):
    db=tmp_path/"auth.db"
    accounts=AccountStore(db)
    accounts.create_user("adminuser","administrator-passphrase",role=Role.ADMIN,status=AccountStatus.ACTIVE)
    admin=accounts.authenticate("adminuser","administrator-passphrase")
    audit=SecurityAuditLog(db)
    mfa=AdminMfaStore(db,audit)
    enrollment=mfa.begin_enrollment(admin)
    import pyotp
    assert mfa.confirm_enrollment(admin,pyotp.TOTP(enrollment.secret).now())
    codes=mfa.generate_recovery_codes(admin)
    assert len(codes)==8 and len(set(codes))==8
    with mfa._connect() as connection:
        rows=connection.execute("SELECT code_hash FROM admin_mfa_recovery WHERE user_id=?",(admin.user_id,)).fetchall()
    stored={row["code_hash"] for row in rows}
    assert codes[0] not in stored
    assert hashlib.sha256(codes[0].encode()).hexdigest() in stored
    assert mfa.verify_recovery_code(admin,codes[0]) is True
    assert mfa.verify_recovery_code(admin,codes[0]) is False
