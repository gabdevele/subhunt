import httpx

from subhunt import alive
from subhunt.models import LiveHost


def test_title_extraction():
    assert alive._title("<html><head><title> Hello </title></head>") == "Hello"
    assert alive._title("no title here") is None


async def test_check_hosts_dns_only_drops_unresolved(monkeypatch):
    async def fake_resolve(hosts, **kwargs):
        return {"a.example.com": ["1.2.3.4"], "dead.example.com": []}

    monkeypatch.setattr(alive, "resolve_all", fake_resolve)
    live = await alive.check_hosts(["a.example.com", "dead.example.com"], dns_only=True)
    assert [item.host for item in live] == ["a.example.com"]
    assert live[0].ips == ["1.2.3.4"]


async def test_check_hosts_probes_resolved(monkeypatch):
    async def fake_resolve(hosts, **kwargs):
        return {host: ["1.2.3.4"] for host in hosts}

    async def fake_probe(hosts, **kwargs):
        return {"a.example.com": ("https://a.example.com", _response())}

    monkeypatch.setattr(alive, "resolve_all", fake_resolve)
    monkeypatch.setattr(alive, "probe_all", fake_probe)
    live = await alive.check_hosts(["a.example.com"])
    assert live == [
        LiveHost(
            host="a.example.com",
            ips=["1.2.3.4"],
            url="https://a.example.com",
            status=200,
            title="Home",
            server="nginx",
        )
    ]


def _response() -> httpx.Response:
    return httpx.Response(
        200,
        text="<title>Home</title>",
        headers={"server": "nginx"},
        request=httpx.Request("GET", "https://a.example.com"),
    )
