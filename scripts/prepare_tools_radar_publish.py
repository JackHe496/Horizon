#!/usr/bin/env python3
"""Keep an unselected radar feed out of a partial GitHub Pages publish."""

from __future__ import annotations

import argparse
from pathlib import Path


def prepare_publish_dir(output: Path, mode: str) -> list[Path]:
    """Remove only the feed that ``keep_files`` must preserve on gh-pages."""
    unselected = {
        "daily": "weekly.json",
        "weekly": "daily.json",
    }.get(mode)
    if not unselected:
        return []

    path = output / unselected
    if not path.exists():
        return []
    path.unlink()
    return [path]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare a partial tools radar publish for GitHub Pages"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/assets/data"),
    )
    parser.add_argument(
        "--mode",
        choices=("all", "daily", "weekly"),
        required=True,
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    removed = prepare_publish_dir(args.output, args.mode)
    for path in removed:
        print(f"Preserving existing gh-pages feed: {path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
