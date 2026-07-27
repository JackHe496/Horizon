"""End-to-end static generation pipeline for the Horizon tools radar."""

from __future__ import annotations

import asyncio
import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from ..ai.client import create_ai_client
from ..models import AIConfig
from .adapters import (
    GitHubSearchAdapter,
    HuggingFaceSpacesAdapter,
    LinuxDoAdapter,
    MCPRegistryAdapter,
    OpenAIPluginsAdapter,
    ProductHuntAdapter,
    SkillsShAdapter,
)
from .analyzer import ToolAIAnalyzer
from .dedup import merge_candidates
from .models import RadarBundle, RadarStatus, SourceRun, Tool, ToolCandidate

ADAPTERS = {
    "github": GitHubSearchAdapter,
    "openai_plugins": OpenAIPluginsAdapter,
    "mcp_registry": MCPRegistryAdapter,
    "product_hunt": ProductHuntAdapter,
    "huggingface_spaces": HuggingFaceSpacesAdapter,
    "skills_sh": SkillsShAdapter,
    "linux_do": LinuxDoAdapter,
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_curated(path: Path) -> list[ToolCandidate]:
    payload = load_json(path)
    return [ToolCandidate.model_validate(item) for item in payload.get("tools", [])]


def _stats(tools: list[Tool], source_runs: list[SourceRun]) -> dict[str, Any]:
    public_tools = [tool for tool in tools if tool.status != RadarStatus.REJECTED]
    return {
        "tool_count": len(public_tools),
        "verified_count": sum(
            tool.status in {RadarStatus.VERIFIED, RadarStatus.TRIED}
            for tool in public_tools
        ),
        "free_first_count": sum(tool.pricing.value == "free" for tool in public_tools),
        "source_count": len({evidence.source_id for tool in tools for evidence in tool.evidence}),
        "categories": dict(Counter(tool.category.value for tool in public_tools)),
        "statuses": dict(Counter(tool.status.value for tool in tools)),
        "source_health": dict(Counter(run.status for run in source_runs)),
    }


def _daily(tools: list[Tool], limit: int = 24) -> list[Tool]:
    visible = [tool for tool in tools if tool.status != RadarStatus.REJECTED]
    return sorted(
        visible,
        key=lambda tool: (
            tool.updated_at,
            tool.status in {RadarStatus.VERIFIED, RadarStatus.TRIED},
            tool.score,
        ),
        reverse=True,
    )[:limit]


def _weekly(tools: list[Tool], limit: int = 12) -> list[Tool]:
    recommended = [
        tool
        for tool in tools
        if tool.status in {RadarStatus.VERIFIED, RadarStatus.TRIED}
    ]
    fallback = [
        tool
        for tool in tools
        if tool.status == RadarStatus.WATCH and tool.source_count >= 2
    ]
    pool = sorted(recommended, key=lambda tool: tool.score, reverse=True)
    if len(pool) < limit:
        pool.extend(sorted(fallback, key=lambda tool: tool.score, reverse=True))

    selected: list[Tool] = []
    category_counts: Counter[str] = Counter()
    for tool in pool:
        if category_counts[tool.category.value] >= 3:
            continue
        selected.append(tool)
        category_counts[tool.category.value] += 1
        if len(selected) >= limit:
            break
    return selected


async def fetch_candidates(
    config: dict[str, Any],
    *,
    offline: bool,
) -> tuple[list[ToolCandidate], list[SourceRun]]:
    curated_path = Path(config.get("curated_path", "data/tools/curated.json"))
    candidates = load_curated(curated_path)
    runs = [
        SourceRun(
            source_id="curated",
            status="success",
            item_count=len(candidates),
        )
    ]
    if offline:
        return candidates, runs

    timeout = httpx.Timeout(30)
    limits = httpx.Limits(max_connections=16, max_keepalive_connections=8)
    async with httpx.AsyncClient(timeout=timeout, limits=limits) as client:
        adapters = []
        for source_id, adapter_type in ADAPTERS.items():
            source_config = config.get("sources", {}).get(source_id, {})
            adapter = adapter_type(source_config, client)
            if adapter.enabled:
                adapters.append(adapter)

        async def fetch_one(adapter):
            try:
                items = await adapter.fetch()
                return items, SourceRun(
                    source_id=adapter.source_id,
                    status="success" if items else "empty",
                    item_count=len(items),
                )
            except Exception as exc:
                return [], SourceRun(
                    source_id=adapter.source_id,
                    status="failure",
                    error=str(exc),
                )

        results = await asyncio.gather(*(fetch_one(adapter) for adapter in adapters))
        for items, run in results:
            candidates.extend(items)
            runs.append(run)
    return candidates, runs


async def build_radar(
    *,
    config_path: Path,
    mode: str = "all",
    offline: bool = False,
    enable_ai: bool = False,
) -> RadarBundle:
    config = load_json(config_path)
    candidates, source_runs = await fetch_candidates(config, offline=offline)

    if enable_ai:
        ai_config_path = Path(config.get("ai_config_path", "data/config.github.json"))
        ai_payload = load_json(ai_config_path)
        ai_config = AIConfig.model_validate(ai_payload["ai"])
        if os.getenv(ai_config.api_key_env, "").strip():
            analyzer = ToolAIAnalyzer(
                create_ai_client(ai_config),
                concurrency=int(config.get("ai", {}).get("concurrency", 4)),
            )
            await analyzer.analyze(
                candidates,
                limit=int(config.get("ai", {}).get("max_candidates", 16)),
            )

    tools = merge_candidates(candidates)
    now = datetime.now(timezone.utc)
    return RadarBundle(
        generated_at=now,
        mode=mode,
        tools=tools,
        source_runs=source_runs,
        stats=_stats(tools, source_runs),
    )


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_bundle(bundle: RadarBundle, output_dir: Path) -> list[Path]:
    generated = bundle.generated_at.isoformat()
    common = {
        "schema_version": bundle.schema_version,
        "generated_at": generated,
    }
    files: list[Path] = []
    tools_path = output_dir / "tools.json"
    _write_json(
        tools_path,
        {
            **common,
            "stats": bundle.stats,
            "tools": [tool.model_dump(mode="json") for tool in bundle.tools],
        },
    )
    files.append(tools_path)

    if bundle.mode in {"all", "daily"}:
        daily_path = output_dir / "daily.json"
        _write_json(
            daily_path,
            {
                **common,
                "period": "daily",
                "tools": [
                    tool.model_dump(mode="json")
                    for tool in _daily(bundle.tools)
                ],
            },
        )
        files.append(daily_path)

    if bundle.mode in {"all", "weekly"}:
        weekly_path = output_dir / "weekly.json"
        _write_json(
            weekly_path,
            {
                **common,
                "period": "weekly",
                "tools": [
                    tool.model_dump(mode="json")
                    for tool in _weekly(bundle.tools)
                ],
            },
        )
        files.append(weekly_path)

    meta_path = output_dir / "meta.json"
    _write_json(
        meta_path,
        {
            **common,
            "mode": bundle.mode,
            "stats": bundle.stats,
            "sources": [run.model_dump(mode="json") for run in bundle.source_runs],
        },
    )
    files.append(meta_path)
    return files
