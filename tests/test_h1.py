from subhunt import h1
from subhunt.models import ScopeAsset, ScopeExclusion


def test_scope_asset_from_api():
    item = {
        "id": "1",
        "attributes": {
            "asset_identifier": "*.example.com",
            "asset_type": "WILDCARD",
            "eligible_for_bounty": True,
            "eligible_for_submission": True,
            "max_severity": "high",
        },
    }
    asset = ScopeAsset.from_api(item)
    assert asset.identifier == "*.example.com"
    assert asset.asset_type == "WILDCARD"
    assert asset.bounty is True
    assert asset.submittable is True


def test_scope_exclusion_from_api():
    item = {"attributes": {"category": "Subdomain takeover", "details": "without POC"}}
    exclusion = ScopeExclusion.from_api(item)
    assert exclusion.category == "Subdomain takeover"
    assert exclusion.details == "without POC"


def test_cached_returns_stored_value(monkeypatch):
    writes = []
    monkeypatch.setattr(h1.cache, "read", lambda key, ttl: {"cached": True})
    monkeypatch.setattr(h1.cache, "write", lambda key, value: writes.append(value))
    assert h1._cached("key", lambda: {"fresh": True}, True, 60) == {"cached": True}
    assert writes == []


def test_cached_computes_and_stores(monkeypatch):
    stored = {}
    monkeypatch.setattr(h1.cache, "read", lambda key, ttl: None)
    monkeypatch.setattr(
        h1.cache, "write", lambda key, value: stored.update({"key": key, "value": value})
    )
    assert h1._cached("key", lambda: {"fresh": True}, True, 60) == {"fresh": True}
    assert stored == {"key": "key", "value": {"fresh": True}}
