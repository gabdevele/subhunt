import hashlib

import httpx
import respx

from subhunt import enrich
from subhunt.models import Enrichment, LiveHost


def _response(status=200, text="", headers=None, content=None, url="https://a.example.com/"):
    return httpx.Response(
        status,
        text=text,
        content=content,
        headers=headers or {},
        request=httpx.Request("GET", url),
    )


def test_missing_security_headers():
    response = _response(headers={"server": "nginx"})
    missing = enrich.missing_headers(response)
    assert "strict-transport-security" in missing
    assert "content-security-policy" in missing


def test_all_security_headers_present():
    response = _response(headers={header: "x" for header in enrich.SECURITY_HEADERS})
    assert enrich.missing_headers(response) == []


def test_detect_tech_from_headers_cookies_body_and_server():
    response = _response(
        text='<link href="/wp-content/style.css">',
        headers={
            "server": "nginx",
            "x-powered-by": "PHP/8.2",
            "cf-ray": "abc123",
            "set-cookie": "csrftoken=abc",
        },
    )
    tech = enrich.detect_tech(response)
    assert {"WordPress", "PHP", "Nginx", "Cloudflare", "Django"} <= set(tech)


@respx.mock
async def test_favicon_hash():
    respx.get("https://a.example.com/favicon.ico").mock(
        return_value=httpx.Response(200, content=b"icon-bytes")
    )
    async with httpx.AsyncClient() as client:
        digest = await enrich.favicon_hash(client, "a.example.com")
    assert digest == hashlib.sha256(b"icon-bytes").hexdigest()[:16]


async def test_detect_takeover(monkeypatch):
    async def fake_cname(host):
        return "foo.github.io"

    monkeypatch.setattr(enrich, "cname_target", fake_cname)
    response = _response(text="There isn't a GitHub Pages site here.")
    assert await enrich.detect_takeover("a.example.com", response) == "GitHub Pages"

    response = _response(text="<html>welcome</html>")
    assert await enrich.detect_takeover("a.example.com", response) is None


def test_enrich_options_active():
    assert not enrich.EnrichOptions().active
    assert enrich.EnrichOptions(enrich=True).active
    assert enrich.EnrichOptions(takeover=True).active


def test_live_host_to_dict_includes_enrichment():
    with_enrichment = LiveHost(
        "a.example.com", ["1.2.3.4"], 200, "Title", "nginx", Enrichment(tech=["Nginx"])
    )
    assert with_enrichment.to_dict()["enrichment"] == {"tech": ["Nginx"]}

    without = LiveHost("b.example.com", [], 404, None, None)
    assert "enrichment" not in without.to_dict()
