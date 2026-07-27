from __future__ import annotations

import asyncio
import json
from pathlib import Path

from src.tools_radar.pipeline import build_radar, write_bundle


def test_offline_pipeline_generates_catalog_daily_weekly_and_meta(tmp_path: Path):
    bundle = asyncio.run(
        build_radar(
            config_path=Path("data/tools-radar.json"),
            mode="all",
            offline=True,
        )
    )
    paths = write_bundle(bundle, tmp_path)

    assert {path.name for path in paths} == {
        "tools.json",
        "daily.json",
        "weekly.json",
        "meta.json",
    }
    catalog = json.loads((tmp_path / "tools.json").read_text())
    weekly = json.loads((tmp_path / "weekly.json").read_text())
    assert catalog["stats"]["tool_count"] >= 20
    assert all(tool["status"] in {"verified", "tried"} for tool in weekly["tools"])
    assert all(tool["install"]["requires_confirmation"] for tool in catalog["tools"])
    context7 = next(tool for tool in catalog["tools"] if tool["name"] == "Context7")
    assert context7["community_signals"]["linux_do_mentions"] == 1
    assert any(
        evidence["source_id"] == "linux-do"
        and evidence["url"] == "https://linux.do/t/topic/702108"
        for evidence in context7["evidence"]
    )


def test_daily_mode_does_not_overwrite_existing_weekly_file(tmp_path: Path):
    weekly = tmp_path / "weekly.json"
    weekly.write_text('{"preserved": true}\n')
    bundle = asyncio.run(
        build_radar(
            config_path=Path("data/tools-radar.json"),
            mode="daily",
            offline=True,
        )
    )

    write_bundle(bundle, tmp_path)

    assert json.loads(weekly.read_text()) == {"preserved": True}
