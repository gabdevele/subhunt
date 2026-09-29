import contextlib
import json
import os
import stat
from dataclasses import dataclass
from pathlib import Path

from platformdirs import user_config_dir

SERVICE = "subhunt"
ACCOUNT = "default"
ENV_USERNAME = "H1_USERNAME"
ENV_TOKEN = "H1_API_TOKEN"

CONFIG_DIR = Path(user_config_dir("subhunt"))
CREDENTIALS_FILE = CONFIG_DIR / "credentials.json"


class CredentialsError(RuntimeError):
    pass


@dataclass(frozen=True)
class Credentials:
    username: str
    token: str


def resolve() -> Credentials | None:
    found, _ = resolve_with_source()
    return found


def source() -> str | None:
    _, origin = resolve_with_source()
    return origin


def resolve_with_source() -> tuple[Credentials | None, str | None]:
    for origin, loader in (("env", _from_env), ("keyring", _from_keyring), ("file", _from_file)):
        found = loader()
        if found is not None:
            return found, origin
    return None, None


def save(username: str, token: str, backend: str = "auto") -> str:
    if backend not in ("auto", "keyring", "file"):
        raise CredentialsError(f"unknown backend: {backend}")
    if backend in ("auto", "keyring") and _store_keyring(username, token):
        return "keyring"
    if backend == "keyring":
        raise CredentialsError("no keyring backend available on this system")
    _store_file(username, token)
    return "file"


def delete() -> list[str]:
    removed = []
    keyring = _keyring()
    if keyring is not None:
        try:
            keyring.delete_password(SERVICE, ACCOUNT)
            removed.append("keyring")
        except keyring.errors.KeyringError:
            pass
    if CREDENTIALS_FILE.exists():
        try:
            CREDENTIALS_FILE.unlink()
            removed.append("file")
        except OSError:
            pass
    return removed


def insecure_permissions() -> bool:
    if not CREDENTIALS_FILE.exists():
        return False
    try:
        mode = CREDENTIALS_FILE.stat().st_mode
    except OSError:
        return False
    return bool(mode & (stat.S_IRWXG | stat.S_IRWXO))


def _keyring():
    try:
        import keyring
    except ImportError:
        return None
    return keyring


def _from_env() -> Credentials | None:
    username = os.environ.get(ENV_USERNAME)
    token = os.environ.get(ENV_TOKEN)
    return Credentials(username, token) if username and token else None


def _from_keyring() -> Credentials | None:
    keyring = _keyring()
    if keyring is None:
        return None
    try:
        raw = keyring.get_password(SERVICE, ACCOUNT)
    except keyring.errors.KeyringError:
        return None
    return _parse(raw)


def _from_file() -> Credentials | None:
    if not CREDENTIALS_FILE.exists():
        return None
    try:
        raw = CREDENTIALS_FILE.read_text(encoding="utf-8")
    except OSError:
        return None
    _restrict_file(CREDENTIALS_FILE)
    return _parse(raw)


def _parse(raw: str | None) -> Credentials | None:
    if not raw:
        return None
    try:
        data = json.loads(raw)
        username, token = data["username"], data["token"]
    except (ValueError, KeyError, TypeError):
        return None
    return Credentials(username, token) if username and token else None


def _store_keyring(username: str, token: str) -> bool:
    keyring = _keyring()
    if keyring is None:
        return False
    try:
        keyring.set_password(SERVICE, ACCOUNT, json.dumps({"username": username, "token": token}))
    except keyring.errors.KeyringError:
        return False
    return True


def _store_file(username: str, token: str) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    _restrict_dir(CONFIG_DIR)
    CREDENTIALS_FILE.write_text(
        json.dumps({"username": username, "token": token}), encoding="utf-8"
    )
    _restrict_file(CREDENTIALS_FILE)


def _restrict_dir(path: Path) -> None:
    with contextlib.suppress(OSError):
        path.chmod(0o700)


def _restrict_file(path: Path) -> None:
    with contextlib.suppress(OSError):
        path.chmod(0o600)
