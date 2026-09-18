from sentinel_alpha.admin_accounts import AdminAccountService
from sentinel_alpha.auth import AccountStatus, AccountStore, Role
from sentinel_alpha.sessions import SessionStore

def setup(tmp_path):
    db=tmp_path/"recovery.db"
    accounts=AccountStore(db)
    accounts.create_user("admin","administrator-passphrase",role=Role.ADMIN,status=AccountStatus.ACTIVE)
    admin=accounts.authenticate("admin","administrator-passphrase")
    target=accounts.create_user("member","member-test-passphrase",status=AccountStatus.ACTIVE)
    return accounts, SessionStore(db), admin, target

def test_enable_only_disabled(tmp_path):
    accounts,sessions,admin,target=setup(tmp_path)
    service=AdminAccountService(accounts,sessions)
    service.set_status(admin,target,AccountStatus.DISABLED)
    service.enable(admin,target)
    assert accounts.authenticate("member","member-test-passphrase") is not None

def test_unlock_only_locked(tmp_path):
    accounts,sessions,admin,target=setup(tmp_path)
    service=AdminAccountService(accounts,sessions)
    service.set_status(admin,target,AccountStatus.LOCKED)
    service.unlock(admin,target)
    assert accounts.authenticate("member","member-test-passphrase") is not None

def test_recovery_transitions_fail_closed(tmp_path):
    accounts,sessions,admin,target=setup(tmp_path)
    service=AdminAccountService(accounts,sessions)
    try:
        service.enable(admin,target)
    except ValueError:
        pass
    else:
        raise AssertionError("active account must not use enable transition")
