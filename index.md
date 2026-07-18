---
layout: default
title: 每日信息雷达
---

# Jack 的 Horizon 每日信息雷达

每天北京时间 **07:00** 自动整理过去 24 小时的重要信息。日报保存在 GitHub 云端，不会每天下载到 Mac。

## 🤖 AI 日报

关注 AI 模型、智能体、科研工具、编程工具、开源项目与行业动态。

<ul>
  {% assign ai_posts = site.posts | where: "topic", "ai" %}
  {% for post in ai_posts limit:30 %}
    <li><a href="{{ post.url | relative_url }}">{{ post.title }}</a></li>
  {% else %}
    <li><em>下一次自动任务完成后显示</em></li>
  {% endfor %}
</ul>

## 🔬 凝聚态与微电子日报

关注凝聚态物理、量子材料、超导、半导体器件、集成电路、芯片制造、光刻、先进封装与行业前景。

<ul>
  {% assign physics_posts = site.posts | where: "topic", "physics-electronics" %}
  {% for post in physics_posts limit:30 %}
    <li><a href="{{ post.url | relative_url }}">{{ post.title }}</a></li>
  {% else %}
    <li><em>下一次自动任务完成后显示</em></li>
  {% endfor %}
</ul>

---

信息源包含公开 RSS、Google News、GitHub、Hacker News、Reddit 与 Telegram；最终由 DeepSeek 进行筛选、背景补充和中文总结。
