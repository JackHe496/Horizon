"""Second-stage synthesis for reader-focused daily reports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .client import AIClient


TOPIC_PROFILES = {
    "ai": """读者是一名中国物理系本科生，想用 AI 提升物理学习、科研和编程能力。
只讨论基础模型、多模态、Agent、AI 编程、科研工具、重要开源项目、模型评测、
安全治理与产业变化。忽略没有直接 AI 关联的泛科技新闻。""",
    "physics-electronics": """读者是一名正在凝聚态物理与微电子/固体电子学之间选择方向的
中国物理系本科生。兼顾凝聚态研究、量子材料、超导、自旋电子学、半导体器件、
集成电路、制造、光刻、封装和产业前景，并明确区分科研信号与产业信号。""",
}


DISTILL_SYSTEM = """你是一名严谨的科技情报编辑和本科生导师。你的任务不是逐条复述新闻，
而是把一份原始日报提炼成可用于判断、学习和行动的中文情报简报。

要求：
- 只使用原始日报提供的事实和链接，不编造新闻、数字、论文结论或来源。
- 主题相关性是硬门槛；离题内容不得进入结论和重点主题。
- 将报道同一趋势的多条新闻聚合成主题，说明共同信号，而不是堆砌标题。
- 区分事实、合理推断和仍不确定的信号；避免夸张。
- 面向大一升大二学生解释意义，语言清楚但不幼稚。
- 直接输出 Markdown，不使用代码块，不写一级标题。

输出结构必须是：
## 今日结论
2-3 段，概括今天最重要的主线与判断。

## 最值得关注的 3 个主题
每个主题使用三级标题，包含：核心信号、关联资讯（使用原文链接）、为什么重要。
如果当天确实不足 3 个主题，可以只写 1-2 个并明确说明样本不足。

## 对我的学习与专业选择意味着什么
给出 3-5 条与本科阶段学习、科研训练、工具使用或专业选择直接相关的启示。

## 明确可执行的下一步
给出最多 3 项今天或本周可以完成的小行动。

## 信号与不确定性
简要说明样本偏差、尚待验证之处，以及不应据此直接下结论的地方。"""


@dataclass(frozen=True)
class MarkdownReport:
    front_matter: str
    body: str


def split_front_matter(markdown: str) -> MarkdownReport:
    """Split optional YAML front matter from a Markdown document."""
    normalized = markdown.lstrip("\ufeff")
    if not normalized.startswith("---\n"):
        return MarkdownReport("", normalized.strip())

    marker = normalized.find("\n---\n", 4)
    if marker == -1:
        return MarkdownReport("", normalized.strip())

    end = marker + len("\n---\n")
    return MarkdownReport(normalized[:end].rstrip(), normalized[end:].strip())


def strip_markdown_fence(text: str) -> str:
    """Remove a single outer Markdown code fence when a model adds one."""
    cleaned = text.strip()
    if not cleaned.startswith("```") or not cleaned.endswith("```"):
        return cleaned

    lines = cleaned.splitlines()
    if len(lines) >= 3:
        return "\n".join(lines[1:-1]).strip()
    return cleaned


def merge_distillation(report: MarkdownReport, distillation: str) -> str:
    """Place distilled analysis before the complete selected-item report."""
    front = f"{report.front_matter}\n\n" if report.front_matter else ""
    return (
        f"{front}{distillation.strip()}\n\n"
        "---\n\n"
        "## 全部入选资讯\n\n"
        f"{report.body.strip()}\n"
    )


class DailyReportDistiller:
    """Generate a second-stage synthesis and merge it into a raw report."""

    def __init__(self, client: "AIClient"):
        self.client = client

    async def distill(self, markdown: str, topic: str) -> str:
        if topic not in TOPIC_PROFILES:
            raise ValueError(f"Unsupported distillation topic: {topic}")

        report = split_front_matter(markdown)
        if not report.body:
            raise ValueError("Cannot distill an empty report")

        source = report.body[:100_000]
        user_prompt = (
            f"## 读者与主题\n{TOPIC_PROFILES[topic]}\n\n"
            "## 原始日报\n"
            f"{source}"
        )
        response = await self.client.complete(
            system=DISTILL_SYSTEM,
            user=user_prompt,
            temperature=0.2,
            max_tokens=6000,
        )
        distillation = strip_markdown_fence(response)
        if "## 今日结论" not in distillation:
            raise ValueError("Distillation response is missing the required conclusion section")
        return merge_distillation(report, distillation)
