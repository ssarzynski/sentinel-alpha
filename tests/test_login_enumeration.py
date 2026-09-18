from sentinel_alpha import auth
from sentinel_alpha.auth import AccountStore

def test_unknown_user_performs_dummy_password_verification(tmp_path, monkeypatch):
    store=AccountStore(tmp_path/"auth.db")
    seen=[]
    original=auth.verify_password
    def observed(password, encoded):
        seen.append(encoded)
        return original(password, encoded)
    monkeypatch.setattr(auth,"verify_password",observed)
    assert store.authenticate("missing-user","incorrect-password") is None
    assert seen == [auth._DUMMY_PASSWORD_HASH]
