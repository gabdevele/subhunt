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


async def test_iter_live_streams_probes(monkeypatch):
    async def fake_resolve(hosts, **kwargs):
        return {host: ["1.2.3.4"] for host in hosts}

    async def fake_stream(alive_hosts, resolved, **kwargs):
        for host in alive_hosts:
            yield LiveHost(
                host=host,
                ips=resolved[host],
                status=200,
                title="Home",
                server="nginx",
            )

    monkeypatch.setattr(alive, "resolve_all", fake_resolve)
    monkeypatch.setattr(alive, "_probe_stream", fake_stream)

    seen = []
    async for host in alive.iter_live(["a.example.com", "b.example.com"]):
        seen.append(host.host)

    assert seen == ["a.example.com", "b.example.com"]
    assert (await alive.check_hosts(["b.example.com", "a.example.com"]))[0].host == "a.example.com"
