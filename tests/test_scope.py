import json
from pathlib import Path

import pytest

from subhunt.models import ScopeAsset
from subhunt.scope import Scope, apex_of, host_pattern, matches

FIXTURES = Path(__file__).parent / "fixtures"


def load_assets() -> list[ScopeAsset]:
    raw = json.loads((FIXTURES / "shopify_scopes.json").read_text())
    return [ScopeAsset.from_api(item) for item in raw]


def test_host_pattern_extracts_hosts_and_wildcards():
    assert host_pattern("*.shopify.com") == "*.shopify.com"
    assert host_pattern("https://*.hackerone-ext-content.com/") == "*.hackerone-ext-content.com"
    assert host_pattern("https://api.example.com/v1") == "api.example.com"
    assert host_pattern("example.com:443") == "example.com"
    assert host_pattern("Shopify Third Party Apps") is None
    assert host_pattern("com.upgrademobile") == "com.upgrademobile"


def test_apex_of_handles_wildcard_shapes():
    assert apex_of("*.shopify.com") == "shopify.com"
    assert apex_of("api.hackerone.com") == "hackerone.com"
    assert apex_of("*ubereats.com") == "ubereats.com"
    assert apex_of("scaledsolutions*.uber.com") == "uber.com"
    assert apex_of("status.*.coinbase.com") == "coinbase.com"


def test_matches_wildcards_and_bare_hosts():
    assert matches("*.example.com", "a.example.com")
    assert matches("*.example.com", "a.b.example.com")
    assert not matches("*.example.com", "example.com")
    assert not matches("*.example.com", "notexample.com")
    assert matches("example.com", "example.com")
    assert matches("example.com", "api.example.com")
    assert matches("*ubereats.com", "x.ubereats.com")


def test_scope_partitions_bounty_assets():
    scope = Scope(program="shopify", assets=load_assets())
    assert scope.in_scope_patterns() == [
        "*.hackerone-ext-content.com",
        "*.shopify.com",
        "*.vpn.example.com",
        "api.example.com",
    ]
    assert scope.out_of_scope_patterns() == ["investors.shopify.com"]
    assert scope.apexes() == ["example.com", "hackerone-ext-content.com", "shopify.com"]


def test_include_non_bounty_widens_scope():
    assets = [ScopeAsset("*.example.com", "WILDCARD", False, True)]
    assert Scope(program="p", assets=assets).in_scope_patterns() == []
    assert Scope(program="p", assets=assets, include_non_bounty=True).in_scope_patterns() == [
        "*.example.com"
    ]


def test_only_wildcards_filters_bare_hosts():
    scope = Scope(program="shopify", assets=load_assets())
    assert scope.in_scope_patterns(only_wildcards=True) == [
        "*.hackerone-ext-content.com",
        "*.shopify.com",
        "*.vpn.example.com",
    ]


def test_keep_applies_in_and_out_of_scope():
    scope = Scope(program="shopify", assets=load_assets())
    hosts = ["a.shopify.com", "investors.shopify.com", "other.org", "x.hackerone-ext-content.com"]
    assert scope.keep(hosts) == ["a.shopify.com", "x.hackerone-ext-content.com"]


@pytest.mark.parametrize("host", ["a.shopify.com", "deep.a.shopify.com"])
def test_keep_wildcard_depth(host: str):
    scope = Scope(program="shopify", assets=load_assets())
    assert scope.keep([host]) == [host]
