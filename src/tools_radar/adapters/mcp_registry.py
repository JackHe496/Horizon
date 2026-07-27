"""Official Model Context Protocol Registry adapter."""

from __future__ import annotations

from datetime import datetime, timezone

from .base import BaseToolAdapter
from ..models import (
    Evidence,
    InstallInfo,
    MaintenanceStatus,
    Maturity,
    PermissionRisk,
    Pricing,
    RadarStatus,
    ToolCandidate,
    ToolCategory,
    ToolKind,
)
from ..security import sanitize_public_url, sanitize_text

REGISTRY_API = "https://registry.modelcontextprotocol.io/v0.1/servers?limit=100"
REGISTRY_DOCS = "https://registry.modelcontextprotocol.io/docs"


class MCPRegistryAdapter(BaseToolAdapter):
    source_id = "mcp-registry"

    async def fetch(self) -> list[ToolCandidate]:
        payload = await self.get_json(REGISTRY_API)
        latest: dict[str, tuple[dict, dict]] = {}
        for record in payload.get("servers", []):
            server = record.get("server") or {}
            meta = (
                record.get("_meta", {})
                .get("io.modelcontextprotocol.registry/official", {})
            )
            name = str(server.get("name") or "")
            if not name or meta.get("status") not in {None, "active"}:
                continue
            existing = latest.get(name)
            if meta.get("isLatest") or existing is None:
                latest[name] = (server, meta)

        limit = max(1, min(int(self.config.get("limit", 30)), 60))
        candidates = [self._candidate(server, meta) for server, meta in latest.values()]
        return sorted(
            candidates,
            key=lambda item: item.updated_at,
            reverse=True,
        )[:limit]

    def _candidate(self, server: dict, meta: dict) -> ToolCandidate:
        registry_name = sanitize_text(server.get("name") or "", max_length=120)
        title = sanitize_text(server.get("title") or registry_name, max_length=120)
        description = sanitize_text(
            server.get("description") or "MCP Registry 收录的工具服务器。",
            max_length=360,
        )
        repository = ""
        repository_info = server.get("repository") or {}
        try:
            repository = sanitize_public_url(repository_info.get("url")) if repository_info else ""
        except Exception:
            repository = ""
        remotes = server.get("remotes") or []
        homepage = repository or REGISTRY_DOCS
        if not repository and remotes:
            try:
                homepage = sanitize_public_url(remotes[0].get("url"))
            except Exception:
                homepage = REGISTRY_DOCS

        packages = server.get("packages") or []
        command = ""
        method = "remote" if remotes else "manual"
        if packages:
            package = packages[0]
            package_type = package.get("registryType")
            identifier = sanitize_text(package.get("identifier") or "", max_length=160)
            if package_type == "npm" and identifier:
                command = f"npx -y {identifier}"
                method = "npm"
            elif package_type in {"pypi", "python"} and identifier:
                command = f"uvx {identifier}"
                method = "uvx"
        published = meta.get("publishedAt") or meta.get("updatedAt")
        updated_at = (
            datetime.fromisoformat(str(published).replace("Z", "+00:00"))
            if published
            else datetime.now(timezone.utc)
        )
        env_vars = sum(
            len(package.get("environmentVariables") or []) for package in packages
        )
        return ToolCandidate(
            source_id=self.source_id,
            source_key=f"mcp:{registry_name}",
            name=title,
            summary_zh=description,
            use_case_zh="为支持 MCP 的 AI 客户端提供外部数据或操作能力。",
            homepage=homepage,
            repository=repository,
            category=ToolCategory.CODEX_ECOSYSTEM,
            kind=ToolKind.MCP,
            pricing=Pricing.UNKNOWN,
            status=RadarStatus.WATCH,
            maturity=Maturity.BETA,
            maintenance=MaintenanceStatus.ACTIVE,
            permission_risk=PermissionRisk.HIGH if env_vars else PermissionRisk.MEDIUM,
            risk_note_zh=(
                f"注册信息声明 {env_vars} 个环境变量；MCP 可扩展模型的外部访问能力，"
                "必须在安装前核查具体工具、数据范围和写入权限。"
            ),
            install=InstallInfo(
                method=method,
                command=command,
                note_zh="Registry 仅提供元数据；安装或连接仍需用户明确确认。",
            ),
            compatibility=["MCP-compatible clients"],
            tags=["MCP", "Official Registry"],
            aliases=[registry_name],
            community_signals={"registry_official": 1},
            evidence=[
                Evidence(
                    source_id=self.source_id,
                    source_name="Official MCP Registry",
                    url=REGISTRY_DOCS,
                    evidence_type="registry",
                    excerpt=f"{registry_name} · version {server.get('version', 'unknown')}。",
                )
            ],
            discovered_at=updated_at,
            updated_at=updated_at,
        )
