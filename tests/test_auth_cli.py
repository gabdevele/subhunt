from typer.testing import CliRunner

from subhunt import cli, credentials
from subhunt.h1 import H1Error

runner = CliRunner()


class FakeClient:
    def __init__(self, username, token, **kwargs):
        self.username = username
        self.token = token

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return None

    def verify(self):
        if self.token != "good":
            raise H1Error("GET /v1/hackers/programs -> 401")


def test_login_stores_token(keyring, config_dir):
    result = runner.invoke(
        cli.app,
        ["auth", "login", "--username", "alice", "--token-stdin", "--no-verify"],
        input="secret\n",
    )
    assert result.exit_code == 0
    assert credentials.resolve() == credentials.Credentials("alice", "secret")
    assert "keyring" in result.stdout


def test_login_verifies_token(monkeypatch, keyring, config_dir):
    monkeypatch.setattr(cli, "H1Client", FakeClient)
    ok = runner.invoke(
        cli.app, ["auth", "login", "--username", "alice", "--token-stdin"], input="good\n"
    )
    assert ok.exit_code == 0
    bad = runner.invoke(
        cli.app, ["auth", "login", "--username", "alice", "--token-stdin"], input="bad\n"
    )
    assert bad.exit_code == 1
    assert credentials.resolve() == credentials.Credentials("alice", "good")


def test_login_prompts_for_hidden_token(keyring, config_dir):
    result = runner.invoke(
        cli.app, ["auth", "login", "--username", "alice", "--no-verify"], input="secret\n"
    )
    assert result.exit_code == 0
    assert credentials.resolve().token == "secret"


def test_login_requires_token(keyring, config_dir):
    result = runner.invoke(
        cli.app,
        ["auth", "login", "--username", "alice", "--token-stdin", "--no-verify"],
        input="\n",
    )
    assert result.exit_code == 1


def test_status_hides_token_and_shows_source(keyring, config_dir):
    credentials.save("alice", "secret", backend="keyring")
    result = runner.invoke(cli.app, ["auth", "status", "--no-verify"])
    assert result.exit_code == 0
    assert "alice" in result.stdout
    assert "keyring" in result.stdout
    assert "secret" not in result.stdout


def test_status_without_credentials(config_dir):
    result = runner.invoke(cli.app, ["auth", "status", "--no-verify"])
    assert result.exit_code == 1


def test_logout_removes_credentials(keyring, config_dir):
    credentials.save("alice", "secret", backend="keyring")
    result = runner.invoke(cli.app, ["auth", "logout"])
    assert result.exit_code == 0
    assert credentials.resolve() is None
