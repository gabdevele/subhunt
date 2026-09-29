import asyncio
import shutil
import subprocess

import httpx

USER_AGENT = "subhunt (+https://github.com/gabdevele/subhunt)"
TIMEOUT = 30.0


def make_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=TIMEOUT,
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
    )


def subfinder_available() -> bool:
    return shutil.which("subfinder") is not None


async def enumerate_domain(
    domain: str, *, client: httpx.AsyncClient, concurrency: int = 10
) -> list[str]:
    if subfinder_available():
        names = await asyncio.to_thread(_run_subfinder, domain)
    else:
        names = await _run_sources(domain, client=client, concurrency=concurrency)
    return sorted(_clean(names, domain))


def _run_subfinder(domain: str) -> set[str]:
    result = subprocess.run(
        ["subfinder", "-d", domain, "-silent"],
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    return set(result.stdout.splitlines())


async def _run_sources(domain: str, *, client: httpx.AsyncClient, concurrency: int) -> set[str]:
    semaphore = asyncio.Semaphore(concurrency)
    tasks = [_guard(source, domain, client, semaphore) for source in SOURCES]
    results = await asyncio.gather(*tasks)
    names: set[str] = set()
    for result in results:
        names |= result
    return names


async def _guard(source, domain, client, semaphore) -> set[str]:
    try:
        return await source(domain, client, semaphore)
    except Exception:
        return set()


async def crtsh(domain: str, client: httpx.AsyncClient, semaphore: asyncio.Semaphore) -> set[str]:
    async with semaphore:
        response = await client.get(
            "https://crt.sh/", params={"q": f"%.{domain}", "output": "json"}
        )
    if response.status_code != 200:
        return set()
    names: list[str] = []
    for entry in response.json():
        names.extend(entry.get("name_value", "").splitlines())
    return set(names)


async def crtname(domain: str, client: httpx.AsyncClient, semaphore: asyncio.Semaphore) -> set[str]:
    async with semaphore:
        response = await client.get("https://crt.name/v1/search", params={"apex": domain})
    return set(response.text.splitlines()) if response.status_code == 200 else set()


async def agniops(domain: str, client: httpx.AsyncClient, semaphore: asyncio.Semaphore) -> set[str]:
    async with semaphore:
        response = await client.get("https://app.agniops.in/v1/search", params={"domain": domain})
    return set(response.text.splitlines()) if response.status_code == 200 else set()


async def jsmon(domain: str, client: httpx.AsyncClient, semaphore: asyncio.Semaphore) -> set[str]:
    names: set[str] = set()
    for page in range(1, 11):
        async with semaphore:
            response = await client.post(
                "https://subdomains.jsmon.sh/api/search",
                json={"domain": domain, "page": page},
            )
        if response.status_code != 200:
            break
        payload = response.json()
        names |= set(payload.get("subdomains") or [])
        if page >= payload.get("total_pages", 1):
            break
    return names


SOURCES = (crtsh, crtname, agniops, jsmon)


def _clean(names, domain: str) -> set[str]:
    domain = domain.strip().lower().strip(".")
    suffix = "." + domain
    cleaned: set[str] = set()
    for raw in names:
        name = raw.strip().lower().lstrip("*.").strip(".")
        if not name or " " in name:
            continue
        if name == domain or name.endswith(suffix):
            cleaned.add(name)
    return cleaned
