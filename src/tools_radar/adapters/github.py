"""GitHub repository search adapter for fast-moving AI tools."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from urllib.parse import quote_plus

from .base import BaseToolAdapter
from ..models import (
    Evidence,
    InstallInfo,
    MaintenanceStatus,
    Maturity,
    PermissionRisk,
    Pricing,
    RadarStatus,
    ToolCandidate,
    ToolCategory,
    ToolKind,
)
from ..security import sanitize_text


class GitHubSearchAdapter(BaseToolAdapter):
    source_id = "github"

    _TOPICS = {
        "ai-coding": ToolCategory.AI_CODING,
        "mcp-server": ToolCategory.CODEX_ECOSYSTEM,
        "ai-agent": ToolCategory.AGENTS_AUTOMATION,
        "research-tool": ToolCategory.SEARCH_RESEARCH,
        "data-analysis": ToolCategory.DATA_ANALYSIS,
    }

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "JackHe496-Horizon-Tools-Radar",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        token = os.getenv("GITHUB_TOKEN", "").strip()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    async def fetch(self) -> list[ToolCandidate]:
        per_query = max(1, min(int(self.config.get("per_query", 8)), 20))
        min_stars = max(0, int(self.config.get("min_stars", 50)))
        pushed_after = (
            datetime.now(timezone.utc) - timedelta(days=int(self.config.get("active_days", 240)))
        ).date()
        candidates: list[ToolCandidate] = []
        for topic, category in self._TOPICS.items():
            query = quote_plus(f"topic:{topic} stars:>={min_stars} pushed:>={pushed_after}")
            url = (
                "https://api.github.com/search/repositories"
                f"?q={query}&sort=updated&order=desc&per_page={per_query}"
            )
            payload = await self.get_json(url, headers=self._headers())
            for repo in payload.get("items", []):
                candidate = self._candidate(repo, category, topic)
                if candidate is not None:
                    candidates.append(candidate)
        return candidates

    def _candidate(
        self, repo: dict, category: ToolCategory, topic: str
    ) -> ToolCandidate | None:
        if repo.get("archived") or repo.get("fork"):
            return None
        name = sanitize_text(repo.get("name") or "", max_length=100)
        html_url = repo.get("html_url") or ""
        if not name or not html_url:
            return None
        stars = int(repo.get("stargazers_count") or 0)
        description = sanitize_text(
            repo.get("description") or f"GitHub 上活跃的 {topic} 开源项目。",
            max_length=320,
        )
        created_at = datetime.fromisoformat(repo["created_at"].replace("Z", "+00:00"))
        updated_at = datetime.fromisoformat(repo["pushed_at"].replace("Z", "+00:00"))
        age_days = max((datetime.now(timezone.utc) - created_at).days, 0)
        maturity = (
            Maturity.STABLE
            if stars >= 5000 and age_days >= 365
            else Maturity.BETA
            if stars >= 500
            else Maturity.EXPERIMENTAL
        )
        return ToolCandidate(
            source_id=self.source_id,
            source_key=f"github:{repo.get('full_name', name)}",
            name=name,
            summary_zh=description,
            use_case_zh="作为候选开源工具进一步核查文档、权限与实际工作流价值。",
            homepage=html_url,
            repository=html_url,
            category=category,
            kind=ToolKind.LIBRARY,
            pricing=Pricing.FREE,
            status=RadarStatus.WATCH,
            maturity=maturity,
            maintenance=MaintenanceStatus.ACTIVE,
            permission_risk=PermissionRisk.MEDIUM,
            risk_note_zh="自动发现项目；安装前需人工检查维护者、依赖、许可证和权限。",
            install=InstallInfo(
                method="manual",
                note_zh="仅提供仓库链接；不自动推断或执行安装命令。",
            ),
            compatibility=["依项目文档"],
            tags=[topic, *list(repo.get("topics") or [])[:8]],
            community_signals={
                "github_stars": stars,
                "github_forks": int(repo.get("forks_count") or 0),
                "open_issues": int(repo.get("open_issues_count") or 0),
            },
            evidence=[
                Evidence(
                    source_id=self.source_id,
                    source_name="GitHub Search",
                    url=html_url,
                    evidence_type="repository",
                    excerpt=f"{stars} stars；最近推送 {updated_at.date().isoformat()}。",
                )
            ],
            discovered_at=created_at,
            updated_at=updated_at,
        )
