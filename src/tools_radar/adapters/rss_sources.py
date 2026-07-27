"""RSS/Atom discovery signals from Product Hunt and LINUX.DO."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from urllib.parse import urljoin, urlsplit

import feedparser
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
from ..security import sanitize_public_url, sanitize_text

PRODUCT_HUNT_FEED = "https://www.producthunt.com/feed"
LINUX_DO_FEED = "https://linux.do/latest.rss?order=created"

_RELEVANCE = {
    ToolCategory.AI_CODING: ("coding", "developer", "code", "编程", "代码", "ide"),
    ToolCategory.CODEX_ECOSYSTEM: ("codex", "plugin", "skill", "mcp", "插件"),
    ToolCategory.AGENTS_AUTOMATION: ("agent", "automation", "workflow", "智能体", "自动化"),
    ToolCategory.SEARCH_RESEARCH: ("research", "search", "paper", "搜索", "研究", "论文"),
    ToolCategory.DATA_ANALYSIS: ("data", "analysis", "analytics", "数据", "分析"),
    ToolCategory.PRODUCTIVITY_LEARNING: (
        "productivity",
        "learning",
        "note",
        "效率",
        "学习",
        "笔记",
    ),
}
_LINUX_EXTERNAL_HOSTS = {
    "github.com",
    "huggingface.co",
    "skills.sh",
    "npmjs.com",
    "pypi.org",
    "modelcontextprotocol.io",
    "openai.com",
}


def _feed_datetime(entry: dict) -> datetime:
    for key in ("published_parsed", "updated_parsed"):
        parsed = entry.get(key)
        if parsed:
            return datetime(*parsed[:6], tzinfo=timezone.utc)
    return datetime.now(timezone.utc)


def _classify(text: str) -> ToolCategory | None:
    lowered = text.casefold()
    best: tuple[int, ToolCategory] | None = None
    for category, keywords in _RELEVANCE.items():
        score = sum(keyword.casefold() in lowered for keyword in keywords)
        if score and (best is None or score > best[0]):
            best = (score, category)
    return best[1] if best else None


class ProductHuntAdapter(BaseToolAdapter):
    source_id = "product-hunt"

    async def fetch(self) -> list[ToolCandidate]:
        feed = feedparser.parse(await self.get_text(PRODUCT_HUNT_FEED))
        limit = max(1, min(int(self.config.get("limit", 20)), 50))
        candidates: list[ToolCandidate] = []
        for entry in feed.entries:
            title = sanitize_text(entry.get("title") or "", max_length=120)
            summary = sanitize_text(
                entry.get("summary") or entry.get("content", [{}])[0].get("value", ""),
                max_length=360,
            )
            category = _classify(f"{title} {summary}")
            if not title or category is None:
                continue
            link = sanitize_public_url(entry.get("link") or PRODUCT_HUNT_FEED)
            published = _feed_datetime(entry)
            candidates.append(
                ToolCandidate(
                    source_id=self.source_id,
                    source_key=f"product-hunt:{entry.get('id') or title}",
                    name=title,
                    summary_zh=summary or "Product Hunt 当日发布的 AI 工具候选。",
                    use_case_zh="作为新品发现信号；进入目录前仍需验证价格、权限和持续维护情况。",
                    homepage=link,
                    category=category,
                    kind=ToolKind.SERVICE,
                    pricing=Pricing.UNKNOWN,
                    status=RadarStatus.NEW,
                    maturity=Maturity.EXPERIMENTAL,
                    maintenance=MaintenanceStatus.UNKNOWN,
                    permission_risk=PermissionRisk.MEDIUM,
                    risk_note_zh="新品信息来自发布页，尚未完成独立安全与价值验证。",
                    install=InstallInfo(
                        method="web",
                        note_zh="仅保留发布页链接，不生成或执行安装命令。",
                    ),
                    compatibility=["Web"],
                    tags=["Product Hunt", "new"],
                    community_signals={"product_hunt_feed": 1},
                    evidence=[
                        Evidence(
                            source_id=self.source_id,
                            source_name="Product Hunt RSS",
                            url=link,
                            evidence_type="launch",
                            excerpt=summary,
                        )
                    ],
                    discovered_at=published,
                    updated_at=published,
                )
            )
            if len(candidates) >= limit:
                break
        return candidates


class LinuxDoAdapter(BaseToolAdapter):
    source_id = "linux-do"

    async def fetch(self) -> list[ToolCandidate]:
        feed = feedparser.parse(await self.get_text(LINUX_DO_FEED))
        limit = max(1, min(int(self.config.get("limit", 16)), 40))
        candidates: list[ToolCandidate] = []
        for entry in feed.entries:
            title = sanitize_text(entry.get("title") or "", max_length=140)
            raw_summary = entry.get("summary") or entry.get("description") or ""
            summary = sanitize_text(raw_summary, max_length=360)
            category = _classify(f"{title} {summary}")
            if category is None:
                continue
            topic_url = sanitize_public_url(
                entry.get("link") or LINUX_DO_FEED,
                allowed_hosts={"linux.do"},
            )
            external = self._external_tool_url(raw_summary)
            if not external:
                continue
            external_host = urlsplit(external).hostname or ""
            name = self._name_from_url(external)
            published = _feed_datetime(entry)
            digest = hashlib.sha256(topic_url.encode()).hexdigest()[:12]
            candidates.append(
                ToolCandidate(
                    source_id=self.source_id,
                    source_key=f"linux-do:{digest}",
                    name=name,
                    summary_zh=title,
                    use_case_zh="来自中文技术社区的发现或讨论信号，需要回到原项目核验。",
                    homepage=external,
                    repository=external if external_host == "github.com" else "",
                    category=category,
                    kind=ToolKind.LIBRARY,
                    pricing=Pricing.UNKNOWN,
                    status=RadarStatus.WATCH,
                    maturity=Maturity.UNKNOWN,
                    maintenance=MaintenanceStatus.UNKNOWN,
                    permission_risk=PermissionRisk.MEDIUM,
                    risk_note_zh="社区讨论不是安全背书；安装前应核查原仓库、维护者和权限。",
                    install=InstallInfo(
                        method="manual",
                        note_zh="仅保留社区发现与原始项目链接。",
                    ),
                    compatibility=["依项目文档"],
                    tags=["LINUX.DO", "community-signal"],
                    community_signals={"linux_do_mentions": 1},
                    evidence=[
                        Evidence(
                            source_id=self.source_id,
                            source_name="LINUX.DO",
                            url=topic_url,
                            evidence_type="community-discussion",
                            excerpt=title,
                        )
                    ],
                    discovered_at=published,
                    updated_at=published,
                )
            )
            if len(candidates) >= limit:
                break
        return candidates

    @staticmethod
    def _external_tool_url(raw_html: str) -> str:
        soup = BeautifulSoup(raw_html, "html.parser")
        for anchor in soup.find_all("a", href=True):
            href = urljoin("https://linux.do", anchor["href"])
            try:
                cleaned = sanitize_public_url(href, allowed_hosts=_LINUX_EXTERNAL_HOSTS)
            except Exception:
                continue
            if (urlsplit(cleaned).hostname or "") != "linux.do":
                return cleaned
        return ""

    @staticmethod
    def _name_from_url(url: str) -> str:
        parsed = urlsplit(url)
        parts = [part for part in parsed.path.split("/") if part]
        if parsed.hostname == "github.com" and len(parts) >= 2:
            return parts[1].removesuffix(".git")
        if parsed.hostname == "huggingface.co" and parts:
            return parts[-1]
        return parts[-1] if parts else (parsed.hostname or "Unknown tool")
