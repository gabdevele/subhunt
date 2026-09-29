import re
from dataclasses import dataclass, field
from functools import cache
from urllib.parse import urlparse

import tldextract

from .models import ScopeAsset, ScopeExclusion

_HOST_TYPES = {"URL", "DOMAIN", "WILDCARD"}
_HOST_RE = re.compile(r"^[a-z0-9*][a-z0-9.*-]*$")
_EXTRACT = tldextract.TLDExtract(suffix_list_urls=())


def host_pattern(identifier: str) -> str | None:
    value = (identifier or "").strip().lower()
    if not value or " " in value:
        return None
    if "://" in value:
        value = urlparse(value).netloc
    value = value.split("/")[0].split(":")[0].strip(".")
    if "." not in value or not _HOST_RE.match(value):
        return None
    return value


def apex_of(pattern: str) -> str | None:
    tail = pattern.rsplit("*", 1)[-1].lstrip(".") if "*" in pattern else pattern
    extracted = _EXTRACT(tail)
    if not extracted.domain or not extracted.suffix:
        return None
    return f"{extracted.domain}.{extracted.suffix}"


@cache
def _glob(pattern: str) -> re.Pattern:
    return re.compile("^" + re.escape(pattern).replace(r"\*", ".*") + "$")


def matches(pattern: str, host: str) -> bool:
    if "*" in pattern:
        return _glob(pattern).match(host) is not None
    return host == pattern or host.endswith("." + pattern)


def _accepts(asset: ScopeAsset) -> bool:
    asset_type = asset.asset_type.upper()
    if asset_type in _HOST_TYPES:
        return True
    return asset_type == "OTHER" and "*" in asset.identifier


@dataclass
class Scope:
    program: str
    assets: list[ScopeAsset]
    exclusions: list[ScopeExclusion] = field(default_factory=list)
    include_non_bounty: bool = False

    def in_scope_patterns(self, only_wildcards: bool = False) -> list[str]:
        assets = [a for a in self.assets if a.submittable and (a.bounty or self.include_non_bounty)]
        return self._patterns(assets, only_wildcards)

    def out_of_scope_patterns(self) -> list[str]:
        return self._patterns([a for a in self.assets if not a.submittable], False)

    def apexes(self, only_wildcards: bool = False) -> list[str]:
        roots = {apex_of(p) for p in self.in_scope_patterns(only_wildcards)}
        return sorted(root for root in roots if root)

    def keep(self, hosts: list[str], only_wildcards: bool = False) -> list[str]:
        in_scope = self.in_scope_patterns(only_wildcards)
        out_scope = self.out_of_scope_patterns()
        return sorted(
            host
            for host in hosts
            if any(matches(p, host) for p in in_scope)
            and not any(matches(p, host) for p in out_scope)
        )

    def _patterns(self, assets: list[ScopeAsset], only_wildcards: bool) -> list[str]:
        patterns = set()
        for asset in assets:
            if not _accepts(asset):
                continue
            pattern = host_pattern(asset.identifier)
            if pattern and (not only_wildcards or "*" in pattern):
                patterns.add(pattern)
        return sorted(patterns)
