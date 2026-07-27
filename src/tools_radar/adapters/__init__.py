"""Source adapters used by the tools radar pipeline."""

from .base import BaseToolAdapter
from .github import GitHubSearchAdapter
from .huggingface import HuggingFaceSpacesAdapter
from .mcp_registry import MCPRegistryAdapter
from .openai_plugins import OpenAIPluginsAdapter
from .rss_sources import LinuxDoAdapter, ProductHuntAdapter
from .skills_sh import SkillsShAdapter

__all__ = [
    "BaseToolAdapter",
    "GitHubSearchAdapter",
    "HuggingFaceSpacesAdapter",
    "LinuxDoAdapter",
    "MCPRegistryAdapter",
    "OpenAIPluginsAdapter",
    "ProductHuntAdapter",
    "SkillsShAdapter",
]
