from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import httpx

from src.tools_radar.adapters.mcp_registry import MCPRegistryAdapter
from src.tools_radar.adapters.rss_sources import LinuxDoAdapter, ProductHuntAdapter
from src.tools_radar.adapters.skills_sh import SkillsShAdapter
from src.tools_radar.models import RadarStatus, ToolKind


def _run(coro):
    return asyncio.run(coro)


def test_mcp_registry_adapter_normalizes_package_without_running_command():
    adapter = MCPRegistryAdapter({}, httpx.AsyncClient())
    adapter.get_json = AsyncMock(
        return_value={
            "servers": [
                {
                    "server": {
                        "name": "io.example/search",
                        "title": "Example Search",
                        "description": "Search external docs.",
                        "version": "1.2.0",
                        "packages": [
                            {
                                "registryType": "npm",
                                "identifier": "@example/search-mcp",
                                "environmentVariables": [{"name": "API_KEY"}],
                            }
                        ],
                        "repository": {
                            "url": "https://github.com/example/search-mcp"
                        },
                    },
                    "_meta": {
                        "io.modelcontextprotocol.registry/official": {
                            "status": "active",
                            "isLatest": True,
                            "publishedAt": "2026-07-01T00:00:00Z",
                        }
                    },
                }
            ]
        }
    )

    tools = _run(adapter.fetch())

    assert len(tools) == 1
    assert tools[0].kind == ToolKind.MCP
    assert tools[0].install.command == "npx -y @example/search-mcp"
    assert tools[0].install.requires_confirmation is True


def test_product_hunt_adapter_filters_irrelevant_items_and_strips_html():
    adapter = ProductHuntAdapter({"limit": 10}, httpx.AsyncClient())
    adapter.get_text = AsyncMock(
        return_value="""<?xml version="1.0"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
          <entry>
            <id>tool-1</id><title>Research Agent</title>
            <link href="https://www.producthunt.com/products/research-agent"/>
            <published>2026-07-27T00:00:00Z</published>
            <content type="html">&lt;b&gt;Search papers&lt;/b&gt;&lt;script&gt;bad()&lt;/script&gt;</content>
          </entry>
          <entry>
            <id>snack-1</id><title>Nice Sandwich</title>
            <link href="https://www.producthunt.com/products/sandwich"/>
            <published>2026-07-27T00:00:00Z</published>
            <content type="html">Lunch delivered.</content>
          </entry>
        </feed>"""
    )

    tools = _run(adapter.fetch())

    assert len(tools) == 1
    assert tools[0].status == RadarStatus.NEW
    assert "<" not in tools[0].summary_zh


def test_skills_sh_adapter_uses_public_skill_links_only():
    adapter = SkillsShAdapter({"limit": 10}, httpx.AsyncClient())
    adapter.get_text = AsyncMock(
        return_value="""
        <a href="/agent/codex">Codex</a>
        <a href="/vercel-labs/skills/find-skills">Find Skills</a>
        <a href="/vercel-labs/skills/find-skills">Duplicate</a>
        <a href="/docs/api">Docs</a>
        """
    )

    tools = _run(adapter.fetch())

    assert len(tools) == 1
    assert tools[0].name == "find skills"
    assert tools[0].install.command == "npx skills add vercel-labs/skills"


def test_linux_do_adapter_requires_relevant_external_tool_link():
    adapter = LinuxDoAdapter({"limit": 10}, httpx.AsyncClient())
    adapter.get_text = AsyncMock(
        return_value="""<rss><channel>
        <item>
          <title>分享一个新的 MCP 搜索工具</title>
          <link>https://linux.do/t/topic/123</link>
          <pubDate>Mon, 27 Jul 2026 00:00:00 +0000</pubDate>
          <description><![CDATA[
            <p>项目地址 <a href="https://github.com/example/search-mcp">GitHub</a></p>
          ]]></description>
        </item>
        <item>
          <title>聊聊 AI</title>
          <link>https://linux.do/t/topic/456</link>
          <description><![CDATA[没有原始项目链接]]></description>
        </item>
        </channel></rss>"""
    )

    tools = _run(adapter.fetch())

    assert len(tools) == 1
    assert tools[0].repository == "https://github.com/example/search-mcp"
    assert tools[0].evidence[0].url == "https://linux.do/t/topic/123"
