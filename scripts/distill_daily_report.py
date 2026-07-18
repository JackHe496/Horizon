#!/usr/bin/env python3
"""Distill one Horizon Markdown report with the configured AI provider."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from dotenv import load_dotenv

from src.ai.client import create_ai_client
from src.ai.distiller import DailyReportDistiller, TOPIC_PROFILES
from src.storage.manager import StorageManager


async def _run(path: Path, topic: str) -> None:
    storage = StorageManager(data_dir="data")
    config = storage.load_config()
    distiller = DailyReportDistiller(create_ai_client(config.ai))
    original = path.read_text(encoding="utf-8")
    result = await distiller.distill(original, topic)
    path.write_text(result, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Add a reader-focused synthesis to a Horizon report")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--topic", required=True, choices=sorted(TOPIC_PROFILES))
    args = parser.parse_args()

    load_dotenv()
    asyncio.run(_run(args.input, args.topic))


if __name__ == "__main__":
    main()
