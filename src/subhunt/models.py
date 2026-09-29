from dataclasses import dataclass, field


@dataclass(frozen=True)
class ScopeAsset:
    identifier: str
    asset_type: str
    bounty: bool
    submittable: bool
    max_severity: str | None = None

    @classmethod
    def from_api(cls, item: dict) -> "ScopeAsset":
        attrs = item.get("attributes") or {}
        return cls(
            identifier=attrs.get("asset_identifier") or "",
            asset_type=attrs.get("asset_type") or "",
            bounty=bool(attrs.get("eligible_for_bounty")),
            submittable=bool(attrs.get("eligible_for_submission")),
            max_severity=attrs.get("max_severity"),
        )


@dataclass(frozen=True)
class ScopeExclusion:
    category: str
    details: str = ""

    @classmethod
    def from_api(cls, item: dict) -> "ScopeExclusion":
        attrs = item.get("attributes") or {}
        return cls(category=attrs.get("category") or "", details=attrs.get("details") or "")


@dataclass
class Enrichment:
    tech: list[str] = field(default_factory=list)
    missing_headers: list[str] = field(default_factory=list)
    tls_issuer: str | None = None
    tls_expires: str | None = None
    tls_sans: list[str] = field(default_factory=list)
    favicon: str | None = None
    takeover: str | None = None

    def to_dict(self) -> dict:
        data: dict = {
            key: getattr(self, key)
            for key in (
                "tech",
                "missing_headers",
                "tls_issuer",
                "tls_expires",
                "tls_sans",
                "favicon",
                "takeover",
            )
            if getattr(self, key)
        }
        return data


@dataclass
class LiveHost:
    host: str
    ips: list[str] = field(default_factory=list)
    status: int | None = None
    title: str | None = None
    server: str | None = None
    enrichment: Enrichment | None = None

    def to_dict(self) -> dict:
        data: dict = {
            "host": self.host,
            "ips": self.ips,
            "status": self.status,
            "title": self.title,
            "server": self.server,
        }
        if self.enrichment:
            data["enrichment"] = self.enrichment.to_dict()
        return data
