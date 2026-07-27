"""Base class and bounded HTTP helpers for tool discovery adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import httpx

from ..models import ToolCandidate
from ..security import safe_request

MAX_RESPONSE_BYTES = 3 * 1024 * 1024


class BaseToolAdapter(ABC):
    source_id = "unknown"

    def __init__(self, config: dict[str, Any], client: httpx.AsyncClient):
        self.config = config
        self.client = client

    @property
    def enabled(self) -> bool:
        return bool(self.config.get("enabled", True))

    async def get(self, url: str, *, headers: dict[str, str] | None = None) -> httpx.Response:
        response = await safe_request(
            self.client,
            "GET",
            url,
            headers=headers or {},
            timeout=25,
        )
        response.raise_for_status()
        content_length = response.headers.get("content-length")
        if content_length and int(content_length) > MAX_RESPONSE_BYTES:
            raise ValueError(f"{self.source_id} response exceeded size limit")
        if len(response.content) > MAX_RESPONSE_BYTES:
            raise ValueError(f"{self.source_id} response exceeded size limit")
        return response

    async def get_json(
        self, url: str, *, headers: dict[str, str] | None = None
    ) -> Any:
        response = await self.get(url, headers=headers)
        return response.json()

    async def get_text(
        self, url: str, *, headers: dict[str, str] | None = None
    ) -> str:
        response = await self.get(url, headers=headers)
        return response.text

    @abstractmethod
    async def fetch(self) -> list[ToolCandidate]:
        """Fetch and normalize one source's candidates."""
