"""Hugging Face Spaces discovery adapter."""

from __future__ import annotations

from datetime import datetime, timezone
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


class HuggingFaceSpacesAdapter(BaseToolAdapter):
    source_id = "huggingface-spaces"

    _QUERIES = {
        "coding agent": ToolCategory.AI_CODING,
        "research agent": ToolCategory.SEARCH_RESEARCH,
        "data analysis": ToolCategory.DATA_ANALYSIS,
    }

    async def fetch(self) -> list[ToolCandidate]:
        per_query = max(1, min(int(self.config.get("per_query", 8)), 20))
        candidates: list[ToolCandidate] = []
        seen: set[str] = set()
        for query, category in self._QUERIES.items():
            url = (
                "https://huggingface.co/api/spaces"
                f"?search={quote_plus(query)}&sort=likes&direction=-1&limit={per_query}"
            )
            payload = await self.get_json(url)
            for space in payload:
                space_id = str(space.get("id") or "")
                if not space_id or space_id in seen or space.get("private"):
                    continue
                seen.add(space_id)
                candidates.append(self._candidate(space, category, query))
        return candidates

    def _candidate(
        self, space: dict, category: ToolCategory, query: str
    ) -> ToolCandidate:
        space_id = sanitize_text(space.get("id") or "", max_length=140)
        name = space_id.rsplit("/", 1)[-1].replace("-", " ").replace("_", " ")
        homepage = f"https://huggingface.co/spaces/{space_id}"
        created = space.get("createdAt")
        updated = space.get("lastModified") or created
        created_at = (
            datetime.fromisoformat(str(created).replace("Z", "+00:00"))
            if created
            else datetime.now(timezone.utc)
        )
        updated_at = (
            datetime.fromisoformat(str(updated).replace("Z", "+00:00"))
            if updated
            else created_at
        )
        likes = int(space.get("likes") or 0)
        tags = [sanitize_text(tag, max_length=60) for tag in (space.get("tags") or [])[:12]]
        return ToolCandidate(
            source_id=self.source_id,
            source_key=f"hf-space:{space_id}",
            name=name,
            summary_zh=f"Hugging Face Spaces 上与“{query}”相关的公开 AI 应用。",
            use_case_zh="先在浏览器中低成本试用，再决定是否值得进入正式工具链。",
            homepage=homepage,
            repository=homepage,
            category=category,
            kind=ToolKind.SPACE,
            pricing=Pricing.FREEMIUM,
            status=RadarStatus.WATCH,
            maturity=Maturity.EXPERIMENTAL,
            maintenance=MaintenanceStatus.ACTIVE,
            permission_risk=PermissionRisk.MEDIUM,
            risk_note_zh="第三方 Space 可能上传数据或调用外部模型；不要提交敏感文件或密钥。",
            install=InstallInfo(
                method="web",
                note_zh="可直接打开公开 Space 试用，无本地自动安装。",
            ),
            compatibility=["Web"],
            tags=["Hugging Face Space", *tags],
            community_signals={"huggingface_likes": likes},
            evidence=[
                Evidence(
                    source_id=self.source_id,
                    source_name="Hugging Face Spaces",
                    url=homepage,
                    evidence_type="community-catalog",
                    excerpt=f"{likes} likes；SDK {space.get('sdk') or 'unknown'}。",
                )
            ],
            discovered_at=created_at,
            updated_at=updated_at,
        )
