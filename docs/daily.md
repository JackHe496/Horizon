---
layout: default
title: AI 与物理日报
description: Horizon 原有 AI、凝聚态物理与微电子中文日报
permalink: /daily/
---

<div class="page-intro">
  <p class="eyebrow"><span></span> EXISTING DAILY DIGESTS</p>
  <h1>AI 与物理日报</h1>
  <p>原有日报继续每天北京时间 <strong>07:00</strong> 运行。工具雷达采用独立流水线，不改变新闻筛选、分析或文章路径。</p>
</div>

## AI 日报

关注 AI 模型、智能体、科研工具、编程工具、开源项目与行业动态。

<ul class="digest-list">
  {% assign ai_posts = site.posts | where: "topic", "ai" %}
  {% for post in ai_posts limit:30 %}
    <li><time>{{ post.date | date: "%Y-%m-%d" }}</time><a href="{{ post.url | relative_url }}">{{ post.title }}</a></li>
  {% else %}
    <li><em>下一次自动任务完成后显示</em></li>
  {% endfor %}
</ul>

## 凝聚态与微电子日报

关注凝聚态物理、量子材料、超导、半导体器件、集成电路、芯片制造、光刻、先进封装与行业前景。

<ul class="digest-list">
  {% assign physics_posts = site.posts | where: "topic", "physics-electronics" %}
  {% for post in physics_posts limit:30 %}
    <li><time>{{ post.date | date: "%Y-%m-%d" }}</time><a href="{{ post.url | relative_url }}">{{ post.title }}</a></li>
  {% else %}
    <li><em>下一次自动任务完成后显示</em></li>
  {% endfor %}
</ul>

---

信息源继续包含公开 RSS、Google News、GitHub、Hacker News、Reddit 与 Telegram；最终由既有 AI 管线进行筛选、背景补充和中文总结。
