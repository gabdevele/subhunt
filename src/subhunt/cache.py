import json
import os
import time
from pathlib import Path
from typing import Any

from platformdirs import user_cache_dir

CACHE_DIR = Path(user_cache_dir("subhunt"))
DEFAULT_TTL = 3600


def _path(key: str) -> Path:
    return CACHE_DIR / f"{key}.json"


def read(key: str, ttl: int = DEFAULT_TTL) -> Any:
    path = _path(key)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if ttl and time.time() - payload.get("time", 0) > ttl:
        return None
    return payload.get("value")


def write(key: str, value: object) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"time": time.time(), "value": value}
    target = _path(key)
    tmp = target.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload), encoding="utf-8")
    os.replace(tmp, target)
