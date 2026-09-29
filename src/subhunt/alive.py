import asyncio
import re

import dns.asyncresolver
import httpx

from .models import LiveHost

USER_AGENT = "subhunt (+https://github.com/gabdevele/subhunt)"
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)


async def resolve_all(
    hosts: list[str], *, concurrency: int = 50, timeout: float = 5.0
) -> dict[str, list[str]]:
    resolver = dns.asyncresolver.Resolver()
    resolver.lifetime = timeout
    semaphore = asyncio.Semaphore(concurrency)

    async def resolve(host: str) -> tuple[str, list[str]]:
        async with semaphore:
            ips: set[str] = set()
            for record in ("A", "AAAA"):
                try:
                    answer = await resolver.resolve(host, record)
                except Exception:
                    continue
                ips |= {str(item) for item in answer}
            return host, sorted(ips)

    pairs = await asyncio.gather(*(resolve(host) for host in hosts))
    return dict(pairs)


async def probe_all(
    hosts: list[str], *, concurrency: int = 25, timeout: float = 10.0
) -> dict[str, tuple[str, httpx.Response]]:
    semaphore = asyncio.Semaphore(concurrency)
    async with httpx.AsyncClient(
        timeout=timeout,
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
        verify=False,
    ) as client:

        async def probe(host: str) -> tuple[str, tuple[str, httpx.Response] | None]:
            async with semaphore:
                for url in (f"https://{host}", f"http://{host}"):
                    try:
                        response = await client.get(url)
                    except httpx.HTTPError:
                        continue
                    return host, (url, response)
            return host, None

        results = await asyncio.gather(*(probe(host) for host in hosts))
    return {host: result for host, result in results if result is not None}


async def check_hosts(
    hosts: list[str],
    *,
    dns_only: bool = False,
    dns_concurrency: int = 50,
    http_concurrency: int = 25,
    timeout: float = 8.0,
) -> list[LiveHost]:
    resolved = await resolve_all(hosts, concurrency=dns_concurrency, timeout=timeout)
    alive = [host for host, ips in resolved.items() if ips]
    if dns_only:
        return [LiveHost(host=host, ips=resolved[host]) for host in sorted(alive)]

    probed = await probe_all(alive, concurrency=http_concurrency, timeout=timeout)
    live = [
        LiveHost(
            host=host,
            ips=resolved[host],
            url=str(response.url),
            status=response.status_code,
            title=_title(response.text),
            server=response.headers.get("server"),
        )
        for host, (url, response) in probed.items()
    ]
    return sorted(live, key=lambda item: item.host)


def _title(html: str) -> str | None:
    match = TITLE_RE.search(html or "")
    return match.group(1).strip()[:120] if match else None
