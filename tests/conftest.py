from __future__ import annotations

import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def stable_example_com_dns(monkeypatch):
    """Keep mocked HTTP tests independent from local DNS interception."""
    from src import url_security

    original = url_security._resolve_hostname

    async def resolve(hostname: str, port: int):
        if hostname.rstrip(".").lower() in {"example.com", "new-url.com"}:
            return {"93.184.216.34"}
        return await original(hostname, port)

    monkeypatch.setattr(url_security, "_resolve_hostname", resolve)
