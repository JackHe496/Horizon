"""Typed data model for tools collected from multiple discovery sources."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from .security import safe_install_command, sanitize_public_url, sanitize_text


class ToolCategory(str, Enum):
    AI_CODING = "ai-coding"
    CODEX_ECOSYSTEM = "codex-ecosystem"
    PRODUCTIVITY_LEARNING = "productivity-learning"
    AGENTS_AUTOMATION = "agents-automation"
    SEARCH_RESEARCH = "search-research"
    DATA_ANALYSIS = "data-analysis"
    OTHER = "other"


class ToolKind(str, Enum):
    APP = "app"
    CLI = "cli"
    LIBRARY = "library"
    PLUGIN = "plugin"
    SKILL = "skill"
    MCP = "mcp"
    SPACE = "space"
    PLATFORM = "platform"
    SERVICE = "service"


class Pricing(str, Enum):
    FREE = "free"
    FREEMIUM = "freemium"
    PAID = "paid"
    UNKNOWN = "unknown"


class RadarStatus(str, Enum):
    NEW = "new"
    WATCH = "watch"
    VERIFIED = "verified"
    TRIED = "tried"
    REJECTED = "rejected"


class Maturity(str, Enum):
    EXPERIMENTAL = "experimental"
    BETA = "beta"
    STABLE = "stable"
    MATURE = "mature"
    UNKNOWN = "unknown"


class MaintenanceStatus(str, Enum):
    ACTIVE = "active"
    MAINTAINED = "maintained"
    STALE = "stale"
    ARCHIVED = "archived"
    UNKNOWN = "unknown"


class PermissionRisk(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Evidence(BaseModel):
    source_id: str
    source_name: str
    url: str
    evidence_type: str = "discovery"
    captured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    excerpt: str = ""

    @field_validator("source_id", "source_name", "evidence_type")
    @classmethod
    def clean_short_text(cls, value: str) -> str:
        return sanitize_text(value, max_length=120)

    @field_validator("excerpt")
    @classmethod
    def clean_excerpt(cls, value: str) -> str:
        return sanitize_text(value, max_length=320)

    @field_validator("url")
    @classmethod
    def clean_url(cls, value: str) -> str:
        return sanitize_public_url(value)


class InstallInfo(BaseModel):
    method: str = "manual"
    command: str = ""
    note_zh: str = ""
    requires_confirmation: bool = True

    @field_validator("method")
    @classmethod
    def clean_method(cls, value: str) -> str:
        return sanitize_text(value, max_length=40).lower()

    @field_validator("command")
    @classmethod
    def clean_command(cls, value: str) -> str:
        return safe_install_command(value)

    @field_validator("note_zh")
    @classmethod
    def clean_note(cls, value: str) -> str:
        return sanitize_text(value, max_length=220)

    @model_validator(mode="after")
    def commands_always_require_confirmation(self) -> "InstallInfo":
        if self.command:
            self.requires_confirmation = True
        return self


class ToolCandidate(BaseModel):
    """One source's claim about a tool, prior to cross-source merging."""

    source_id: str
    source_key: str
    name: str
    name_zh: str = ""
    summary_zh: str
    use_case_zh: str = ""
    homepage: str
    repository: str = ""
    category: ToolCategory = ToolCategory.OTHER
    kind: ToolKind = ToolKind.APP
    pricing: Pricing = Pricing.UNKNOWN
    status: RadarStatus = RadarStatus.NEW
    maturity: Maturity = Maturity.UNKNOWN
    maintenance: MaintenanceStatus = MaintenanceStatus.UNKNOWN
    permission_risk: PermissionRisk = PermissionRisk.MEDIUM
    risk_note_zh: str = ""
    install: InstallInfo = Field(default_factory=InstallInfo)
    compatibility: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)
    community_signals: dict[str, float | int | str] = Field(default_factory=dict)
    evidence: list[Evidence] = Field(default_factory=list)
    discovered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    curated: bool = False

    @field_validator("source_id", "source_key", "name")
    @classmethod
    def clean_identity_text(cls, value: str) -> str:
        return sanitize_text(value, max_length=160)

    @field_validator(
        "name_zh",
        "summary_zh",
        "use_case_zh",
        "risk_note_zh",
    )
    @classmethod
    def clean_descriptive_text(cls, value: str) -> str:
        return sanitize_text(value, max_length=600)

    @field_validator("homepage")
    @classmethod
    def clean_homepage(cls, value: str) -> str:
        return sanitize_public_url(value)

    @field_validator("repository")
    @classmethod
    def clean_repository(cls, value: str) -> str:
        return sanitize_public_url(value) if value else ""

    @field_validator("compatibility", "tags", "aliases")
    @classmethod
    def clean_string_list(cls, values: list[str]) -> list[str]:
        cleaned: list[str] = []
        for value in values[:24]:
            item = sanitize_text(value, max_length=80)
            if item and item.casefold() not in {existing.casefold() for existing in cleaned}:
                cleaned.append(item)
        return cleaned

    @model_validator(mode="after")
    def require_evidence(self) -> "ToolCandidate":
        if not self.evidence:
            raise ValueError("tool candidates require at least one source evidence record")
        if self.status in {RadarStatus.TRIED, RadarStatus.REJECTED} and not self.curated:
            raise ValueError("tried/rejected statuses require manual curation")
        return self


class Tool(BaseModel):
    id: str
    name: str
    name_zh: str = ""
    summary_zh: str
    use_case_zh: str = ""
    homepage: str
    repository: str = ""
    category: ToolCategory
    kind: ToolKind
    pricing: Pricing
    status: RadarStatus
    maturity: Maturity
    maintenance: MaintenanceStatus
    permission_risk: PermissionRisk
    risk_note_zh: str = ""
    install: InstallInfo
    compatibility: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)
    community_signals: dict[str, float | int | str] = Field(default_factory=dict)
    evidence: list[Evidence]
    discovered_at: datetime
    updated_at: datetime
    source_count: int = Field(default=1, ge=1)
    score: float = 0

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,95}", value):
            raise ValueError("tool id must be a stable lowercase slug")
        return value


class SourceRun(BaseModel):
    source_id: str
    status: str
    item_count: int = 0
    error: str = ""

    @field_validator("source_id", "status")
    @classmethod
    def clean_status_text(cls, value: str) -> str:
        return sanitize_text(value, max_length=80)

    @field_validator("error")
    @classmethod
    def clean_error(cls, value: str) -> str:
        return sanitize_text(value, max_length=240)


class RadarBundle(BaseModel):
    schema_version: str = "1.0"
    generated_at: datetime
    mode: str
    tools: list[Tool]
    source_runs: list[SourceRun] = Field(default_factory=list)
    stats: dict[str, Any] = Field(default_factory=dict)
