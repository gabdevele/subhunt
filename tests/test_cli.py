import json

from typer.testing import CliRunner

from subhunt import cli
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


def test_scan_json(monkeypatch):
    monkeypatch.setattr(cli, "_scope_for", lambda handle, include, cache: Scope(handle, ASSETS))

    async def fake_enumerate(apexes, concurrency):
        return ["a.example.com"]

    async def fake_check(hosts, **kwargs):
        return [
            LiveHost("a.example.com", ["1.2.3.4"], "https://a.example.com/", 200, "Home", "nginx")
        ]

    monkeypatch.setattr(cli, "_enumerate", fake_enumerate)
    monkeypatch.setattr(cli, "check_hosts", fake_check)

    result = runner.invoke(cli.app, ["scan", "example", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.stdout)[0]["host"] == "a.example.com"


def test_scan_without_scope_exits(monkeypatch):
    monkeypatch.setattr(cli, "_scope_for", lambda handle, include, cache: Scope(handle, []))
    result = runner.invoke(cli.app, ["scan", "example"])
    assert result.exit_code == 1
