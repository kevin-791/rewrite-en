import pytest

from rewrite_en import keystore


class FakeKeyring:
    def __init__(self):
        self.store = {}

    def get_password(self, service, user):
        return self.store.get((service, user))

    def set_password(self, service, user, value):
        self.store[(service, user)] = value

    def delete_password(self, service, user):
        self.store.pop((service, user), None)


@pytest.fixture
def fake_keyring(monkeypatch):
    kr = FakeKeyring()
    monkeypatch.setattr(keystore, "keyring", kr)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    return kr


@pytest.mark.req("REQ-SEC-1")
def test_keychain_first_then_env(fake_keyring, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-env")
    assert keystore.get_api_key() == "sk-env"
    keystore.set_api_key("  sk-keychain \n")
    assert keystore.get_api_key() == "sk-keychain"


@pytest.mark.req("REQ-SEC-1")
def test_missing_key_raises(fake_keyring):
    with pytest.raises(keystore.MissingAPIKey):
        keystore.get_api_key()
    with pytest.raises(ValueError):
        keystore.set_api_key("   ")
