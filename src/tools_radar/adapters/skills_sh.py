"""Skills.sh public leaderboard signal adapter."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

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

SKILLS_SH_URL = "https://skills.sh/"
_SKILL_PATH = re.compile(r"^/([^/]+)/([^/]+)/([^/?#]+)$")
_EXCLUDED_PREFIXES = {"agent", "topic", "docs", "audits", "official", "site"}


class SkillsShAdapter(BaseToolAdapter):
    source_id = "skills-sh"

    async def fetch(self) -> list[ToolCandidate]:
        soup = BeautifulSoup(await self.get_text(SKILLS_SH_URL), "html.parser")
        limit = max(1, min(int(self.config.get("limit", 24)), 60))
        candidates: list[ToolCandidate] = []
        seen: set[str] = set()
        rank = 0
        for anchor in soup.find_all("a", href=True):
            path = urlsplit(anchor["href"]).path
            match = _SKILL_PATH.fullmatch(path)
            if not match or match.group(1) in _EXCLUDED_PREFIXES:
                continue
            owner, repo, skill = match.groups()
            skill_id = f"{owner}/{repo}/{skill}"
            if skill_id in seen:
                continue
            seen.add(skill_id)
            rank += 1
            name = skill.replace("-", " ").replace("_", " ")
            page_url = f"https://skills.sh/{skill_id}"
            repository = f"https://github.com/{owner}/{repo}"
            candidates.append(
                ToolCandidate(
                    source_id=self.source_id,
                    source_key=f"skill:{skill_id}",
                    name=name,
                    summary_zh=f"Skills.sh 排行榜中的 Agent Skill：{skill}。",
                    use_case_zh="为兼容的编码 Agent 增加可复用流程知识；使用前应阅读完整 SKILL.md。",
                    homepage=page_url,
                    repository=repository,
                    category=self._classify(name),
                    kind=ToolKind.SKILL,
                    pricing=Pricing.FREE,
                    status=RadarStatus.WATCH,
                    maturity=Maturity.UNKNOWN,
                    maintenance=MaintenanceStatus.UNKNOWN,
                    permission_risk=PermissionRisk.HIGH,
                    risk_note_zh="Skill 是可执行工作流说明，可能要求脚本、联网或外部工具；安装前必须人工审阅。",
                    install=InstallInfo(
                        method="npx-skills",
                        command=f"npx skills add {owner}/{repo}",
                        note_zh="排行榜命令仅供复制；实际安装必须先获得用户明确确认。",
                    ),
                    compatibility=["Codex", "Claude Code", "兼容 Agent Skills 的客户端"],
                    tags=["Agent Skill", "Skills.sh"],
                    aliases=[skill],
                    community_signals={"skills_sh_rank": rank},
                    evidence=[
                        Evidence(
                            source_id=self.source_id,
                            source_name="Skills.sh",
                            url=page_url,
                            evidence_type="community-leaderboard",
                            excerpt=f"公开排行榜第 {rank} 个发现信号。",
                        )
                    ],
                    discovered_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
            )
            if len(candidates) >= limit:
                break
        return candidates

    @staticmethod
    def _classify(name: str) -> ToolCategory:
        lowered = name.casefold()
        if any(word in lowered for word in ("research", "paper", "search")):
            return ToolCategory.SEARCH_RESEARCH
        if any(word in lowered for word in ("data", "postgres", "analytics")):
            return ToolCategory.DATA_ANALYSIS
        if any(word in lowered for word in ("plan", "workflow", "agent", "automation")):
            return ToolCategory.AGENTS_AUTOMATION
        if any(word in lowered for word in ("code", "frontend", "react", "debug", "test")):
            return ToolCategory.AI_CODING
        return ToolCategory.CODEX_ECOSYSTEM
