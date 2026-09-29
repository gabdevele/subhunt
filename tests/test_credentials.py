import json

from subhunt import credentials


def test_save_and_resolve_via_keyring(keyring, config_dir):
    assert credentials.save("alice", "secret", backend="auto") == "keyring"
    assert credentials.resolve() == credentials.Credentials("alice", "secret")
    assert credentials.source() == "keyring"
    assert not config_dir.joinpath("credentials.json").exists()


def test_save_falls_back_to_file(monkeypatch, config_dir):
    monkeypatch.setattr(credentials, "_keyring", lambda: None)
    assert credentials.save("alice", "secret", backend="auto") == "file"
    assert credentials.resolve() == credentials.Credentials("alice", "secret")
    assert credentials.source() == "file"


def test_file_permissions_are_restricted(monkeypatch, config_dir):
    monkeypatch.setattr(credentials, "_keyring", lambda: None)
    credentials.save("alice", "secret", backend="file")
    mode = (config_dir / "credentials.json").stat().st_mode & 0o777
    assert mode == 0o600
    assert credentials.insecure_permissions() is False


def test_insecure_permissions_detected(monkeypatch, config_dir):
    monkeypatch.setattr(credentials, "_keyring", lambda: None)
    credentials.save("alice", "secret", backend="file")
    (config_dir / "credentials.json").chmod(0o644)
    assert credentials.insecure_permissions() is True


def test_env_has_precedence(monkeypatch, keyring, config_dir):
    monkeypatch.setenv(credentials.ENV_USERNAME, "envuser")
    monkeypatch.setenv(credentials.ENV_TOKEN, "envtoken")
    credentials.save("fileuser", "filetoken", backend="file")
    assert credentials.source() == "env"
    assert credentials.resolve() == credentials.Credentials("envuser", "envtoken")


def test_delete_removes_keyring_and_file(monkeypatch, keyring, config_dir):
    credentials.save("alice", "secret", backend="keyring")
    credentials.save("alice", "secret", backend="file")
    assert sorted(credentials.delete()) == ["file", "keyring"]
    assert credentials.resolve() is None


def test_parse_rejects_malformed(config_dir):
    (config_dir / "credentials.json").write_text(json.dumps({"username": "alice"}))
    assert credentials.resolve() is None


def test_save_rejects_unknown_backend(config_dir):
    try:
        credentials.save("alice", "secret", backend="vault")
    except credentials.CredentialsError:
        return
    raise AssertionError("expected CredentialsError")
