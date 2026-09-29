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
        attrs = item.get("attributes") or item
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
        attrs = item.get("attributes") or item
        return cls(category=attrs.get("category") or "", details=attrs.get("details") or "")


@dataclass
class LiveHost:
    host: str
    ips: list[str] = field(default_factory=list)
    url: str | None = None
    status: int | None = None
    title: str | None = None
    server: str | None = None

    def to_dict(self) -> dict:
        return {
            "host": self.host,
            "ips": self.ips,
            "url": self.url,
            "status": self.status,
            "title": self.title,
            "server": self.server,
        }
