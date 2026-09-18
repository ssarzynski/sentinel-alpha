from datetime import datetime, timedelta, timezone
import pytest
from sentinel_alpha.auth import AccountStatus, Role, UserAccount, require_admin

def account(*,must_change=False,expires=None):
    return UserAccount(1,"admin",Role.ADMIN,AccountStatus.ACTIVE,must_change,(expires or (datetime.now(timezone.utc)+timedelta(days=1))).isoformat())

def test_admin_boundary_rejects_forced_password_change():
    with pytest.raises(PermissionError,match="password change required"):
        require_admin(account(must_change=True))

def test_admin_boundary_rejects_expired_password():
    with pytest.raises(PermissionError,match="password change required"):
        require_admin(account(expires=datetime.now(timezone.utc)-timedelta(seconds=1)))

def test_admin_boundary_accepts_current_active_admin():
    require_admin(account())
