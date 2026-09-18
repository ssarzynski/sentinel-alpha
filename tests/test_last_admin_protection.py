import pytest
from sentinel_alpha.admin_accounts import AdminAccountService
from sentinel_alpha.auth import AccountStatus, AccountStore, Role
from sentinel_alpha.sessions import SessionStore

def setup(db):
    accounts=AccountStore(db)
    accounts.create_user("admin-one","administrator-passphrase",role=Role.ADMIN,status=AccountStatus.ACTIVE)
    admin=accounts.authenticate("admin-one","administrator-passphrase")
    return accounts, admin, AdminAccountService(accounts,SessionStore(db))

def test_last_active_admin_cannot_be_disabled(tmp_path):
    accounts, admin, service=setup(tmp_path/"a.db")
    with pytest.raises(ValueError,match="last active administrator"):
        service.set_status(admin,admin.user_id,AccountStatus.DISABLED)

def test_last_active_admin_cannot_be_demoted_by_another_admin_state(tmp_path):
    accounts, admin, service=setup(tmp_path/"b.db")
    accounts.create_user("admin-two","second-admin-passphrase",role=Role.ADMIN,status=AccountStatus.ACTIVE)
    second=accounts.authenticate("admin-two","second-admin-passphrase")
    service.set_role(admin,second.user_id,Role.USER)
    with pytest.raises(ValueError,match="last active administrator"):
        service.set_role(admin,admin.user_id,Role.USER)
