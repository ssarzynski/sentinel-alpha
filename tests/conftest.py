import pytest
from cryptography.fernet import Fernet

@pytest.fixture(autouse=True)
def sentinel_mfa_encryption_key(monkeypatch):
    monkeypatch.setenv("SENTINEL_MFA_ENCRYPTION_KEY", Fernet.generate_key().decode())
