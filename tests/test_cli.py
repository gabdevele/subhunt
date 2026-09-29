import asyncio
import json

import pytest
import typer
from typer.testing import CliRunner

from subhunt import cli, credentials
from subhunt.models import LiveHost, ScopeAsset
from subhunt.scope import Scope

runner = CliRunner()

ASSETS = [ScopeAsset("*.example.com", "WILDCARD", True, True)]


def test_version():
    result = runner.invoke(cli.app, ["--version"])
    assert result.exit_code == 0
    assert "subhunt" in result.stdout


def test_scope_command(monkeypatch):
    monkeypatch.setattr(cli, "_scope_for", lambda handle, include, cache: Scope(handle, ASSETS))
    result = runner.invoke(cli.app, ["scope", "example"])
    assert result.exit_code == 0
    assert "*.example.com" in result.stdout


def _fake_scan(stream: bool):
    async def fake_scan(scope, apexes, **kwargs):
        host = LiveHost("a.example.com", ["1.2.3.4"], 200, "Home", "nginx")
        if stream:
            kwargs["on_host"](host)
        return [host]

    return fake_scan


def test_scan_json(monkeypatch):
    monkeypatch.setattr(cli, "_scope_for", lambda handle, include, cache: Scope(handle, ASSETS))
    monkeypatch.setattr(cli, "_scan_stream", _fake_scan(stream=False))

    result = runner.invoke(cli.app, ["scan", "example", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.stdout)[0]["host"] == "a.example.com"


def test_scan_streams_findings_by_default(monkeypatch):
    monkeypatch.setattr(cli, "_scope_for", lambda handle, include, cache: Scope(handle, ASSETS))
    monkeypatch.setattr(cli, "_scan_stream", _fake_scan(stream=True))

    result = runner.invoke(cli.app, ["scan", "example"])
    assert result.exit_code == 0
    assert "a.example.com" in result.stdout
    assert "200" in result.stdout


def test_scan_without_scope_exits(monkeypatch):
    monkeypatch.setattr(cli, "_scope_for", lambda handle, include, cache: Scope(handle, []))
    result = runner.invoke(cli.app, ["scan", "example"])
    assert result.exit_code == 1


def test_scan_writes_json_file(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "_scope_for", lambda handle, include, cache: Scope(handle, ASSETS))
    monkeypatch.setattr(cli, "_scan_stream", _fake_scan(stream=False))

    out = tmp_path / "out.json"
    result = runner.invoke(cli.app, ["scan", "example", "--json", "-o", str(out)])
    assert result.exit_code == 0
    assert json.loads(out.read_text())[0]["host"] == "a.example.com"


def test_parse_status_codes():
    assert cli._parse_status_codes("200,404") == {200, 404}
    assert cli._parse_status_codes("200") == {200}
    assert cli._parse_status_codes(None) is None


def test_parse_status_codes_rejects_invalid():
    with pytest.raises(typer.BadParameter):
        cli._parse_status_codes("200,abc")


def test_build_headers_parses_and_substitutes(monkeypatch):
    monkeypatch.setenv(credentials.ENV_USERNAME, "alice")
    monkeypatch.setenv(credentials.ENV_TOKEN, "tok")
    headers = cli._build_headers(["X-Bug-Bounty: HackerOne-{username}", "X-Foo: bar"], False)
    assert headers == {"X-Bug-Bounty": "HackerOne-alice", "X-Foo": "bar"}


def test_build_headers_h1_shorthand(monkeypatch):
    monkeypatch.setenv(credentials.ENV_USERNAME, "alice")
    monkeypatch.setenv(credentials.ENV_TOKEN, "tok")
    assert cli._build_headers([], True) == {"X-HackerOne-Research": "alice"}


def test_build_headers_rejects_invalid():
    with pytest.raises(typer.BadParameter):
        cli._build_headers(["no-colon"], False)


def test_build_headers_requires_credentials_for_placeholder(config_dir):
    with pytest.raises(typer.BadParameter):
        cli._build_headers(["X-User: {username}"], False)


def test_status_code_with_dns_only_is_rejected(monkeypatch):
    monkeypatch.setattr(cli, "_scope_for", lambda handle, include, cache: Scope(handle, ASSETS))
    result = runner.invoke(cli.app, ["scan", "example", "--status-code", "200", "--dns-only"])
    assert result.exit_code != 0


def test_scan_stream_filters_by_status(monkeypatch):
    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return None

    async def fake_enumerate(apex, client=None, concurrency=1):
        return ["a.example.com", "b.example.com"]

    async def fake_iter(hosts, **kwargs):
        yield LiveHost("a.example.com", ["1.1.1.1"], 200, "A", "nginx")
        yield LiveHost("b.example.com", ["1.1.1.2"], 404, "B", "nginx")

    monkeypatch.setattr(cli, "make_client", FakeClient)
    monkeypatch.setattr(cli, "enumerate_domain", fake_enumerate)
    monkeypatch.setattr(cli, "iter_live", fake_iter)

    seen: list[str] = []
    live = asyncio.run(
        cli._scan_stream(
            Scope("example", ASSETS),
            ["example.com"],
            only_wildcards=False,
            dns_only=False,
            concurrency=1,
            timeout=1.0,
            on_host=seen.append,
            status_codes={200},
        )
    )
    assert [host.host for host in live] == ["a.example.com"]
    assert [host.host for host in seen] == ["a.example.com"]
