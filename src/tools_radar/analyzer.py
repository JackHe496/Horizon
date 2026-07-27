"""Optional Chinese-first AI analysis that reuses Horizon's AI client."""

from __future__ import annotations

import asyncio
import json
import re

from pydantic import BaseModel, ValidationError

from ..ai.client import AIClient
from ..ai.utils import parse_json_response
from .models import (
    Maturity,
    PermissionRisk,
    Pricing,
    ToolCandidate,
    ToolCategory,
)
from .security import sanitize_text

_HAN = re.compile(r"[\u3400-\u9fff]")

SYSTEM_PROMPT = """你是个人 AI 工具雷达的审慎编辑。请根据给定名称、原始说明和来源，
返回严格 JSON，不要返回 Markdown。不要编造价格、安装命令、兼容性、下载量或安全结论。
只允许以下字段：
- summary_zh: 一句简洁中文说明，可保留英文产品名；
- use_case_zh: 一句说明适合解决什么问题；
- category: ai-coding / codex-ecosystem / productivity-learning /
  agents-automation / search-research / data-analysis / other；
- pricing: free / freemium / paid / unknown；
- maturity: experimental / beta / stable / mature / unknown；
- permission_risk: none / low / medium / high / critical；
- risk_note_zh: 说明需要人工确认的最主要权限或数据风险。
如果证据不足，pricing、maturity 必须使用 unknown，风险宁可偏保守。"""


class ToolAnalysis(BaseModel):
    summary_zh: str
    use_case_zh: str
    category: ToolCategory
    pricing: Pricing
    maturity: Maturity
    permission_risk: PermissionRisk
    risk_note_zh: str


class ToolAIAnalyzer:
    def __init__(self, client: AIClient, *, concurrency: int = 4):
        self.client = client
        self.concurrency = max(1, min(concurrency, 8))

    async def analyze(
        self, candidates: list[ToolCandidate], *, limit: int = 16
    ) -> list[ToolCandidate]:
        targets = [
            candidate
            for candidate in candidates
            if not candidate.curated or not _HAN.search(candidate.summary_zh)
        ][: max(0, limit)]
        semaphore = asyncio.Semaphore(self.concurrency)

        async def process(candidate: ToolCandidate) -> None:
            async with semaphore:
                try:
                    await self._analyze_one(candidate)
                except Exception:
                    return

        await asyncio.gather(*(process(candidate) for candidate in targets))
        return candidates

    async def _analyze_one(self, candidate: ToolCandidate) -> None:
        evidence = [
            {
                "source": item.source_name,
                "type": item.evidence_type,
                "excerpt": item.excerpt,
            }
            for item in candidate.evidence[:4]
        ]
        response = await self.client.complete(
            system=SYSTEM_PROMPT,
            user=json.dumps(
                {
                    "name": candidate.name,
                    "current_summary": candidate.summary_zh,
                    "kind": candidate.kind.value,
                    "source_evidence": evidence,
                },
                ensure_ascii=False,
            ),
            temperature=0.1,
            max_tokens=700,
        )
        parsed = parse_json_response(response)
        try:
            result = ToolAnalysis.model_validate(parsed)
        except ValidationError:
            return
        candidate.summary_zh = sanitize_text(result.summary_zh, max_length=360)
        candidate.use_case_zh = sanitize_text(result.use_case_zh, max_length=280)
        candidate.category = result.category
        if candidate.pricing == Pricing.UNKNOWN:
            candidate.pricing = result.pricing
        if candidate.maturity == Maturity.UNKNOWN:
            candidate.maturity = result.maturity
        candidate.permission_risk = max(
            (candidate.permission_risk, result.permission_risk),
            key=lambda risk: list(PermissionRisk).index(risk),
        )
        candidate.risk_note_zh = sanitize_text(result.risk_note_zh, max_length=280)
