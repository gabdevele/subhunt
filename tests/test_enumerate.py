import asyncio

import httpx
import respx

from subhunt import enumerate


def test_clean_keeps_only_domain_hosts():
    names = ["*.a.example.com", "b.example.com", "evil.com", "x.example.com.evil.com", "bad host"]
    assert enumerate._clean(names, "example.com") == {"a.example.com", "b.example.com"}


@respx.mock
async def test_crtsh_reads_name_value():
    respx.get("https://crt.sh/").mock(
        return_value=httpx.Response(200, json=[{"name_value": "a.example.com\n*.b.example.com"}])
    )
    async with httpx.AsyncClient() as client:
        names = await enumerate.crtsh("example.com", client, asyncio.Semaphore(1))
    assert names == {"a.example.com", "*.b.example.com"}


@respx.mock
async def test_jsmon_paginates():
    respx.post("https://subdomains.jsmon.sh/api/search").mock(
        return_value=httpx.Response(200, json={"subdomains": ["a.example.com"], "total_pages": 1})
    )
    async with httpx.AsyncClient() as client:
        names = await enumerate.jsmon("example.com", client, asyncio.Semaphore(1))
    assert names == {"a.example.com"}


async def test_enumerate_domain_uses_builtin_sources(monkeypatch):
    async def fake_source(domain, client, semaphore):
        return {f"a.{domain}", f"b.{domain}", "evil.org"}

    monkeypatch.setattr(enumerate, "subfinder_available", lambda: False)
    monkeypatch.setattr(enumerate, "SOURCES", (fake_source,))
    async with httpx.AsyncClient() as client:
        hosts = await enumerate.enumerate_domain("example.com", client=client)
    assert hosts == ["a.example.com", "b.example.com"]
