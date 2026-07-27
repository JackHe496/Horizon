from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.tools_radar.models import Evidence, InstallInfo, RadarStatus, ToolCandidate


def _candidate(**overrides):
    payload = {
        "source_id": "test",
        "source_key": "test:tool",
        "name": "Test Tool",
        "summary_zh": "测试工具。",
        "homepage": "https://example.com/tool",
        "evidence": [
            Evidence(
                source_id="test",
                source_name="Test source",
                url="https://example.com/evidence",
            )
        ],
    }
    payload.update(overrides)
    return ToolCandidate(**payload)


def test_install_command_always_requires_confirmation():
    install = InstallInfo(command="npx example", requires_confirmation=False)
    assert install.requires_confirmation is True


def test_automated_source_cannot_claim_tried_or_rejected():
    for status in (RadarStatus.TRIED, RadarStatus.REJECTED):
        with pytest.raises(ValidationError, match="manual curation"):
            _candidate(status=status)


def test_candidate_requires_traceable_evidence():
    with pytest.raises(ValidationError, match="at least one"):
        _candidate(evidence=[])
