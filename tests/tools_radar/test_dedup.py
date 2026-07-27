from __future__ import annotations

from src.tools_radar.dedup import merge_candidates
from src.tools_radar.models import (
    Evidence,
    Pricing,
    RadarStatus,
    ToolCandidate,
)


def _candidate(source_id, homepage, *, name="Context7", **overrides):
    payload = {
        "source_id": source_id,
        "source_key": f"{source_id}:context7",
        "name": name,
        "summary_zh": "按版本检索开发文档。",
        "homepage": homepage,
        "pricing": Pricing.UNKNOWN,
        "status": RadarStatus.WATCH,
        "evidence": [
            Evidence(
                source_id=source_id,
                source_name=source_id,
                url=f"https://example.com/{source_id}",
            )
        ],
    }
    payload.update(overrides)
    return ToolCandidate(**payload)


def test_same_github_repository_merges_and_keeps_all_evidence():
    first = _candidate(
        "github",
        "https://github.com/upstash/context7",
        repository="https://github.com/upstash/context7",
    )
    second = _candidate(
        "linux-do",
        "https://github.com/upstash/context7/?utm_source=community",
        repository="https://github.com/upstash/context7",
    )

    tools = merge_candidates([first, second])

    assert len(tools) == 1
    assert tools[0].source_count == 2
    assert {item.source_id for item in tools[0].evidence} == {"github", "linux-do"}


def test_curated_status_and_price_win_over_automatic_candidates():
    automatic = _candidate("github", "https://example.com/context7")
    curated = _candidate(
        "curated",
        "https://example.com/context7",
        status=RadarStatus.VERIFIED,
        pricing=Pricing.FREE,
        curated=True,
    )

    tool = merge_candidates([automatic, curated])[0]

    assert tool.status == RadarStatus.VERIFIED
    assert tool.pricing == Pricing.FREE


def test_similar_but_nonidentical_names_do_not_merge_without_shared_identity():
    tools = merge_candidates(
        [
            _candidate("one", "https://example.com/alpha", name="Agent Search"),
            _candidate("two", "https://example.org/beta", name="Agent Search Pro"),
        ]
    )
    assert len(tools) == 2
