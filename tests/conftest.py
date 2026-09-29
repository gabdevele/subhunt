import pytest

from subhunt import credentials


class FakeKeyring:
    def __init__(self) -> None:
        self.values: dict[tuple[str, str], str] = {}

    def get_password(self, service, account):
        return self.values.get((service, account))

    def set_password(self, service, account, value):
        self.values[(service, account)] = value

    def delete_password(self, service, account):
        del self.values[(service, account)]


@pytest.fixture(autouse=True)
def no_keyring(monkeypatch):
    monkeypatch.setattr(credentials, "_keyring", lambda: None)


@pytest.fixture
def keyring(monkeypatch):
    fake = FakeKeyring()
    monkeypatch.setattr(credentials, "_keyring", lambda: fake)
    return fake


@pytest.fixture
def config_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(credentials, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(credentials, "CREDENTIALS_FILE", tmp_path / "credentials.json")
    monkeypatch.delenv(credentials.ENV_USERNAME, raising=False)
    monkeypatch.delenv(credentials.ENV_TOKEN, raising=False)
    return tmp_path
