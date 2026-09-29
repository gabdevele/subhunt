import asyncio
import re

import dns.asyncresolver
import dns.exception
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
                except dns.exception.DNSException:
                    continue
                ips |= {str(item) for item in answer}
            return host, sorted(ips)

    pairs = await asyncio.gather(*(resolve(host) for host in hosts))
    return dict(pairs)


async def iter_live(
    hosts: list[str],
    *,
    dns_only: bool = False,
    dns_concurrency: int = 50,
    http_concurrency: int = 25,
    timeout: float = 8.0,
    enricher=None,
    headers: dict[str, str] | None = None,
):
    """Yield each reachable host as soon as it is discovered and enriched."""
    resolved = await resolve_all(hosts, concurrency=dns_concurrency, timeout=timeout)
    alive = sorted(host for host, ips in resolved.items() if ips)

    if dns_only:
        for host in alive:
            yield LiveHost(host=host, ips=resolved[host])
        return

    async for live in _probe_stream(
        alive,
        resolved,
        concurrency=http_concurrency,
        timeout=timeout,
        enricher=enricher,
        headers=headers,
    ):
        yield live


async def check_hosts(hosts: list[str], **kwargs) -> list[LiveHost]:
    return sorted([item async for item in iter_live(hosts, **kwargs)], key=lambda item: item.host)


async def _probe_stream(
    alive: list[str],
    resolved: dict[str, list[str]],
    *,
    concurrency: int,
    timeout: float,
    enricher=None,
    headers: dict[str, str] | None = None,
):
    semaphore = asyncio.Semaphore(concurrency)
    async with httpx.AsyncClient(
        timeout=timeout,
        headers={"User-Agent": USER_AGENT, **(headers or {})},
        follow_redirects=True,
        verify=False,
    ) as client:

        async def probe(host: str) -> tuple[str, httpx.Response | None]:
            async with semaphore:
                for url in (f"https://{host}", f"http://{host}"):
                    try:
                        response = await client.get(url)
                    except httpx.HTTPError:
                        continue
                    return host, response
            return host, None

        tasks = [probe(host) for host in alive]
        for coro in asyncio.as_completed(tasks):
            host, response = await coro
            if response is None:
                continue
            live = LiveHost(
                host=host,
                ips=resolved[host],
                status=response.status_code,
                title=_title(response.text),
                server=response.headers.get("server"),
            )
            if enricher is not None:
                try:
                    live.enrichment = await enricher(host, response, client)
                except (httpx.HTTPError, dns.exception.DNSException):
                    live.enrichment = None
            yield live


def _title(html: str) -> str | None:
    match = TITLE_RE.search(html or "")
    return match.group(1).strip()[:120] if match else None
