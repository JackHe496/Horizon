"""OpenAI's public curated plugin marketplace adapter."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

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

MARKETPLACE_URL = (
    "https://raw.githubusercontent.com/openai/plugins/main/"
    ".agents/plugins/marketplace.json"
)
REPOSITORY_URL = "https://github.com/openai/plugins"

_CATEGORY_MAP = {
    "Developer Tools": ToolCategory.CODEX_ECOSYSTEM,
    "Productivity": ToolCategory.PRODUCTIVITY_LEARNING,
    "Communication": ToolCategory.PRODUCTIVITY_LEARNING,
    "Education & Research": ToolCategory.SEARCH_RESEARCH,
    "Data & Analytics": ToolCategory.DATA_ANALYSIS,
}


class OpenAIPluginsAdapter(BaseToolAdapter):
    source_id = "openai-plugins"

    async def fetch(self) -> list[ToolCandidate]:
        marketplace = await self.get_json(MARKETPLACE_URL)
        entries = [
            entry
            for entry in marketplace.get("plugins", [])
            if entry.get("policy", {}).get("installation") != "NOT_AVAILABLE"
        ]
        limit = max(1, min(int(self.config.get("limit", 40)), 80))
        entries = self._prioritize(entries)[:limit]
        semaphore = asyncio.Semaphore(8)

        async def load(entry: dict) -> ToolCandidate:
            async with semaphore:
                return await self._candidate(entry)

        return list(await asyncio.gather(*(load(entry) for entry in entries)))

    @staticmethod
    def _prioritize(entries: list[dict]) -> list[dict]:
        priority = {
            "github",
            "hugging-face",
            "deepnote",
            "notion",
            "zotero",
            "figma",
            "google-drive",
            "build-web-apps",
            "build-web-data-visualization",
            "plugin-eval",
            "coderabbit",
            "cloudflare",
            "sentry",
            "vercel",
            "netlify",
        }
        return sorted(
            entries,
            key=lambda item: (
                item.get("name") not in priority,
                item.get("category") not in _CATEGORY_MAP,
                item.get("name", ""),
            ),
        )

    async def _candidate(self, entry: dict) -> ToolCandidate:
        name = sanitize_text(entry.get("name") or "", max_length=90)
        path = entry.get("source", {}).get("path", f"./plugins/{name}")
        relative_path = str(path).removeprefix("./")
        manifest_url = (
            "https://raw.githubusercontent.com/openai/plugins/main/"
            f"{relative_path}/.codex-plugin/plugin.json"
        )
        manifest: dict = {}
        try:
            manifest = await self.get_json(manifest_url)
        except Exception:
            manifest = {}
        interface = manifest.get("interface") or {}
        display_name = sanitize_text(interface.get("displayName") or name, max_length=100)
        description = sanitize_text(
            interface.get("shortDescription")
            or interface.get("longDescription")
            or f"OpenAI 官方目录中的 {display_name} 插件。",
            max_length=360,
        )
        category_name = entry.get("category") or interface.get("category") or ""
        category = _CATEGORY_MAP.get(category_name, ToolCategory.OTHER)
        products = entry.get("policy", {}).get("products") or ["CHATGPT", "CODEX"]
        repository_path = f"{REPOSITORY_URL}/tree/main/{relative_path}"
        auth_mode = entry.get("policy", {}).get("authentication", "ON_INSTALL")
        risk = (
            PermissionRisk.HIGH
            if category_name in {"Communication", "Finance", "Business & Operations"}
            else PermissionRisk.MEDIUM
        )
        return ToolCandidate(
            source_id=self.source_id,
            source_key=f"openai-plugin:{name}",
            name=display_name,
            summary_zh=description,
            use_case_zh="把可复用工作流或已连接的数据源带入 ChatGPT/Codex。",
            homepage=repository_path,
            repository=repository_path,
            category=category,
            kind=ToolKind.PLUGIN,
            pricing=Pricing.UNKNOWN,
            status=RadarStatus.VERIFIED,
            maturity=Maturity.STABLE,
            maintenance=MaintenanceStatus.ACTIVE,
            permission_risk=risk,
            risk_note_zh=(
                f"官方清单要求 {auth_mode} 授权；实际权限取决于插件绑定的连接器，"
                "安装和连接前需逐项确认。"
            ),
            install=InstallInfo(
                method="codex-plugin",
                command=f"codex plugin add {name}@openai-curated",
                note_zh="命令仅供复制；安装前必须由用户明确确认。",
            ),
            compatibility=[str(product).title() for product in products],
            tags=["OpenAI", "Codex Plugin", category_name],
            aliases=[name],
            community_signals={"official_curated": 1},
            evidence=[
                Evidence(
                    source_id=self.source_id,
                    source_name="OpenAI Plugins",
                    url=repository_path,
                    evidence_type="official-marketplace",
                    excerpt=f"OpenAI curated marketplace；分类 {category_name or 'Other'}。",
                )
            ],
            discovered_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
