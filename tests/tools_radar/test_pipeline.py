from __future__ import annotations

import asyncio
import json
from pathlib import Path

from scripts.prepare_tools_radar_publish import prepare_publish_dir
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


def test_partial_publish_removes_only_the_feed_keep_files_must_preserve(
    tmp_path: Path,
):
    daily = tmp_path / "daily.json"
    weekly = tmp_path / "weekly.json"
    daily.write_text('{"feed": "daily"}\n')
    weekly.write_text('{"feed": "weekly"}\n')

    removed = prepare_publish_dir(tmp_path, "weekly")

    assert removed == [daily]
    assert not daily.exists()
    assert weekly.exists()

    daily.write_text('{"feed": "daily"}\n')
    removed = prepare_publish_dir(tmp_path, "daily")

    assert removed == [weekly]
    assert daily.exists()
    assert not weekly.exists()
