import asyncio

from src.ai.distiller import DailyReportDistiller, split_front_matter


RAW_REPORT = """---
layout: default
title: Test
---

> 从 10 条内容中筛选出 2 条重要资讯。

1. [Item A](https://example.com/a)
2. [Item B](https://example.com/b)
"""


class FakeClient:
    async def complete(self, **kwargs):
        assert "Item A" in kwargs["user"]
        assert "物理系本科生" in kwargs["user"]
        return """## 今日结论
今天出现一个清晰信号。

## 最值得关注的 3 个主题
### 主题一
关联资讯：[Item A](https://example.com/a)

## 对我的学习与专业选择意味着什么
- 学习基础工具。

## 明确可执行的下一步
- 阅读原文。

## 信号与不确定性
样本有限。
"""


def test_split_front_matter():
    report = split_front_matter(RAW_REPORT)
    assert report.front_matter.startswith("---")
    assert "layout: default" in report.front_matter
    assert report.body.startswith("> 从 10 条内容")


def test_distill_merges_synthesis_before_raw_items():
    result = asyncio.run(DailyReportDistiller(FakeClient()).distill(RAW_REPORT, "ai"))
    assert result.index("## 今日结论") < result.index("## 全部入选资讯")
    assert "[Item B](https://example.com/b)" in result
    assert result.count("layout: default") == 1
