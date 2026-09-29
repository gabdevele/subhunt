import time
from collections.abc import Callable
from dataclasses import asdict
from typing import TypeVar

import httpx

from . import cache, credentials
from .models import ScopeAsset, ScopeExclusion
from .scope import Scope

BASE_URL = "https://api.hackerone.com"
MAX_RETRIES = 3
MAX_RETRY_DELAY = 30.0
PAGE_SIZE = 100


class H1Error(RuntimeError):
    pass


class CredentialsMissing(H1Error):
    pass


def _retry_delay(response: httpx.Response) -> float:
    try:
        seconds = float(response.headers.get("Retry-After", 1))
    except ValueError:
        seconds = 1.0
    return min(max(seconds, 0.0), MAX_RETRY_DELAY)


class H1Client:
    def __init__(self, username: str, token: str, timeout: float = 30.0) -> None:
        self._client = httpx.Client(
            base_url=BASE_URL,
            auth=(username, token),
            timeout=timeout,
            headers={"Accept": "application/json"},
        )

    @classmethod
    def from_credentials(cls) -> "H1Client":
        found = credentials.resolve()
        if found is None:
            raise CredentialsMissing(
                "no HackerOne credentials found; run 'subhunt auth login' "
                "or set H1_USERNAME and H1_API_TOKEN"
            )
        return cls(found.username, found.token)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "H1Client":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _get(self, path: str, params: dict | None = None) -> dict:
        for attempt in range(MAX_RETRIES + 1):
            response = self._client.get(path, params=params)
            if response.status_code == 429 and attempt < MAX_RETRIES:
                time.sleep(_retry_delay(response))
                continue
            if response.status_code >= 400:
                raise H1Error(f"GET {path} -> {response.status_code}")
            return response.json()
        raise H1Error(f"GET {path} -> rate limited")

    def structured_scopes(self, handle: str) -> list[ScopeAsset]:
        assets: list[ScopeAsset] = []
        for page in range(1, 11):
            payload = self._get(
                f"/v1/hackers/programs/{handle}/structured_scopes",
                {"page[number]": page, "page[size]": PAGE_SIZE},
            )
            batch = payload.get("data") or []
            assets.extend(ScopeAsset.from_api(item) for item in batch)
            if len(batch) < PAGE_SIZE:
                break
        return assets

    def scope_exclusions(self, handle: str) -> list[ScopeExclusion]:
        payload = self._get(f"/v1/hackers/programs/{handle}/scope_exclusions")
        return [ScopeExclusion.from_api(item) for item in payload.get("data") or []]

    def verify(self) -> None:
        self._get("/v1/hackers/programs", {"page[number]": 1, "page[size]": 1})


T = TypeVar("T")


def _cached(key: str, produce: Callable[[], T], use_cache: bool, ttl: int) -> T:
    if use_cache:
        value = cache.read(key, ttl)
        if value is not None:
            return value
    value = produce()
    if use_cache:
        cache.write(key, value)
    return value


def load_scope(
    client: H1Client,
    handle: str,
    *,
    include_non_bounty: bool = False,
    use_cache: bool = True,
    ttl: int = cache.DEFAULT_TTL,
) -> Scope:
    raw_assets = _cached(
        f"h1-scopes-{handle}",
        lambda: [asdict(asset) for asset in client.structured_scopes(handle)],
        use_cache,
        ttl,
    )
    raw_exclusions = _cached(
        f"h1-exclusions-{handle}",
        lambda: [asdict(exclusion) for exclusion in client.scope_exclusions(handle)],
        use_cache,
        ttl,
    )
    return Scope(
        program=handle,
        assets=[ScopeAsset(**item) for item in raw_assets],
        exclusions=[ScopeExclusion(**item) for item in raw_exclusions],
        include_non_bounty=include_non_bounty,
    )
