"""Conservative cross-source identity matching and merge logic."""

from __future__ import annotations

import hashlib
import math
import re
from collections import defaultdict
from dataclasses import dataclass
from urllib.parse import urlsplit

from .models import (
    MaintenanceStatus,
    Maturity,
    PermissionRisk,
    Pricing,
    RadarStatus,
    Tool,
    ToolCandidate,
)

_STATUS_RANK = {
    RadarStatus.REJECTED: -100,
    RadarStatus.NEW: 10,
    RadarStatus.WATCH: 20,
    RadarStatus.VERIFIED: 40,
    RadarStatus.TRIED: 50,
}
_MATURITY_RANK = {
    Maturity.UNKNOWN: 0,
    Maturity.EXPERIMENTAL: 1,
    Maturity.BETA: 2,
    Maturity.STABLE: 3,
    Maturity.MATURE: 4,
}
_MAINTENANCE_RANK = {
    MaintenanceStatus.ARCHIVED: -2,
    MaintenanceStatus.STALE: -1,
    MaintenanceStatus.UNKNOWN: 0,
    MaintenanceStatus.MAINTAINED: 1,
    MaintenanceStatus.ACTIVE: 2,
}
_RISK_RANK = {
    PermissionRisk.NONE: 0,
    PermissionRisk.LOW: 1,
    PermissionRisk.MEDIUM: 2,
    PermissionRisk.HIGH: 3,
    PermissionRisk.CRITICAL: 4,
}


def normalized_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def canonical_url(value: str) -> str:
    parsed = urlsplit(value)
    host = (parsed.hostname or "").lower()
    path_parts = [part for part in parsed.path.split("/") if part]
    if host in {"github.com", "www.github.com"} and len(path_parts) >= 2:
        return f"github.com/{path_parts[0].casefold()}/{path_parts[1].removesuffix('.git').casefold()}"
    if host in {"huggingface.co", "www.huggingface.co"} and len(path_parts) >= 3:
        if path_parts[0] == "spaces":
            return "huggingface.co/spaces/" + "/".join(part.casefold() for part in path_parts[1:3])
    if host in {"skills.sh", "www.skills.sh"} and len(path_parts) >= 3:
        return "skills.sh/" + "/".join(part.casefold() for part in path_parts[:3])
    return f"{host}{parsed.path.rstrip('/') or '/'}".casefold()


def identity_keys(candidate: ToolCandidate) -> set[str]:
    keys = {f"url:{canonical_url(candidate.homepage)}"}
    if candidate.repository:
        keys.add(f"repo:{canonical_url(candidate.repository)}")
    name = normalized_name(candidate.name)
    if len(name) >= 4:
        keys.add(f"name:{name}")
    for alias in candidate.aliases:
        alias_key = normalized_name(alias)
        if len(alias_key) >= 4:
            keys.add(f"name:{alias_key}")
    return keys


@dataclass
class _UnionFind:
    parents: list[int]

    @classmethod
    def create(cls, size: int) -> "_UnionFind":
        return cls(list(range(size)))

    def find(self, item: int) -> int:
        while self.parents[item] != item:
            self.parents[item] = self.parents[self.parents[item]]
            item = self.parents[item]
        return item

    def union(self, left: int, right: int) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root != right_root:
            self.parents[right_root] = left_root


def _stable_slug(candidate: ToolCandidate) -> str:
    raw = re.sub(r"[^a-z0-9]+", "-", candidate.name.casefold()).strip("-")
    raw = raw[:72] or "tool"
    digest = hashlib.sha256(canonical_url(candidate.homepage).encode()).hexdigest()[:8]
    return f"{raw}-{digest}"


def _preferred(candidates: list[ToolCandidate]) -> ToolCandidate:
    curated = [candidate for candidate in candidates if candidate.curated]
    pool = curated or candidates
    return max(
        pool,
        key=lambda item: (
            _STATUS_RANK[item.status],
            len(item.summary_zh),
            len(item.evidence),
        ),
    )


def _merge_status(candidates: list[ToolCandidate]) -> RadarStatus:
    curated = [candidate.status for candidate in candidates if candidate.curated]
    statuses = curated or [candidate.status for candidate in candidates]
    if RadarStatus.REJECTED in curated:
        return RadarStatus.REJECTED
    return max(statuses, key=_STATUS_RANK.__getitem__)


def _merge_pricing(candidates: list[ToolCandidate]) -> Pricing:
    preferred = _preferred(candidates)
    if preferred.pricing != Pricing.UNKNOWN:
        return preferred.pricing
    return next(
        (candidate.pricing for candidate in candidates if candidate.pricing != Pricing.UNKNOWN),
        Pricing.UNKNOWN,
    )


def _merge_dict(candidates: list[ToolCandidate]) -> dict[str, float | int | str]:
    merged: dict[str, float | int | str] = {}
    for candidate in candidates:
        for key, value in candidate.community_signals.items():
            existing = merged.get(key)
            if isinstance(value, (int, float)) and isinstance(existing, (int, float)):
                merged[key] = max(existing, value)
            elif key not in merged:
                merged[key] = value
    return merged


def _score(tool: Tool) -> float:
    status_points = _STATUS_RANK[tool.status] * 2
    price_points = {
        Pricing.FREE: 16,
        Pricing.FREEMIUM: 8,
        Pricing.UNKNOWN: 0,
        Pricing.PAID: -6,
    }[tool.pricing]
    evidence_points = min(tool.source_count * 5, 20)
    maintenance_points = _MAINTENANCE_RANK[tool.maintenance] * 5
    risk_penalty = _RISK_RANK[tool.permission_risk] * 3
    community_points = 0.0
    for value in tool.community_signals.values():
        if isinstance(value, (int, float)) and value > 0:
            community_points += min(math.log10(value + 1) * 2.5, 8)
    return round(
        status_points
        + price_points
        + evidence_points
        + maintenance_points
        + community_points
        - risk_penalty,
        2,
    )


def merge_candidates(candidates: list[ToolCandidate]) -> list[Tool]:
    """Merge exact canonical URL, repository, or exact-name matches."""
    if not candidates:
        return []
    union_find = _UnionFind.create(len(candidates))
    seen: dict[str, int] = {}
    for index, candidate in enumerate(candidates):
        for key in identity_keys(candidate):
            if key in seen:
                union_find.union(index, seen[key])
            else:
                seen[key] = index

    groups: dict[int, list[ToolCandidate]] = defaultdict(list)
    for index, candidate in enumerate(candidates):
        groups[union_find.find(index)].append(candidate)

    tools: list[Tool] = []
    for group in groups.values():
        preferred = _preferred(group)
        evidence_by_url = {}
        for candidate in group:
            for evidence in candidate.evidence:
                evidence_by_url[(evidence.source_id, evidence.url)] = evidence
        list_fields = {}
        for field in ("compatibility", "tags", "aliases"):
            values: list[str] = []
            for candidate in group:
                for value in getattr(candidate, field):
                    if value.casefold() not in {item.casefold() for item in values}:
                        values.append(value)
            list_fields[field] = values

        maturity = max(group, key=lambda item: _MATURITY_RANK[item.maturity]).maturity
        maintenance = max(
            group, key=lambda item: _MAINTENANCE_RANK[item.maintenance]
        ).maintenance
        risk = max(group, key=lambda item: _RISK_RANK[item.permission_risk]).permission_risk
        tool = Tool(
            id=_stable_slug(preferred),
            name=preferred.name,
            name_zh=preferred.name_zh,
            summary_zh=preferred.summary_zh,
            use_case_zh=preferred.use_case_zh,
            homepage=preferred.homepage,
            repository=preferred.repository,
            category=preferred.category,
            kind=preferred.kind,
            pricing=_merge_pricing(group),
            status=_merge_status(group),
            maturity=maturity,
            maintenance=maintenance,
            permission_risk=risk,
            risk_note_zh=preferred.risk_note_zh,
            install=preferred.install,
            compatibility=list_fields["compatibility"],
            tags=list_fields["tags"],
            aliases=list_fields["aliases"],
            community_signals=_merge_dict(group),
            evidence=list(evidence_by_url.values()),
            discovered_at=min(candidate.discovered_at for candidate in group),
            updated_at=max(candidate.updated_at for candidate in group),
            source_count=len({evidence.source_id for evidence in evidence_by_url.values()}),
        )
        tool.score = _score(tool)
        tools.append(tool)

    return sorted(
        tools,
        key=lambda item: (
            item.status == RadarStatus.REJECTED,
            -item.score,
            item.name.casefold(),
        ),
    )
