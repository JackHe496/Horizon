#!/usr/bin/env python3
"""Generate static JSON for Horizon's personal AI tools radar."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from src.tools_radar.pipeline import build_radar, write_bundle


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Horizon tools radar assets")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("data/tools-radar.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/assets/data"),
    )
    parser.add_argument(
        "--mode",
        choices=("all", "daily", "weekly"),
        default="all",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Use curated data only; make no network requests.",
    )
    parser.add_argument(
        "--ai",
        action="store_true",
        help="Use the existing Horizon AI provider when its key is configured.",
    )
    return parser.parse_args()


async def run() -> int:
    args = parse_args()
    bundle = await build_radar(
        config_path=args.config,
        mode=args.mode,
        offline=args.offline,
        enable_ai=args.ai,
    )
    paths = write_bundle(bundle, args.output)
    failed_sources = sum(run.status == "failure" for run in bundle.source_runs)
    print(
        f"Generated {len(bundle.tools)} merged tools in {len(paths)} files; "
        f"{failed_sources} source(s) failed."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
