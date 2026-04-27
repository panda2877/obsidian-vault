---
id: hermes-vs-openclaw
tags: [comparison, hermes, openclaw]
created: 2026-04-27
source: 01-学习/ai学习/Hermes Agent架构说明.md
---

# Hermes vs OpenClaw

两个主流开源Agent框架的对比。

## 核心差异

| 维度 | Hermes | OpenClaw |
|------|--------|----------|
| 自进化 | 有后台技能复盘机制 | 不明确 |
| 子Agent | 支持delegate_task委托 | 视实现 |
| 平台适配 | 20+平台适配器 | 不明确 |
| 记忆 | MEMORY.md/USER.md + 8个Provider | 不明确 |

## 共同点

- 都走适配器模式统一多平台消息
- 都有迭代预算/轮次限制
- 都支持工具并行

## 相关链接

  - [[Hermes Agent主体]]
  - [[AIAgent主循环]]
  - [[自进化机制]]
  - [[子Agent委托]]
