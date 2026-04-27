---
id: chinese-prompt-injection
tags: [query, hermes, security]
created: 2026-04-27
source: 01-学习/ai学习/Hermes Agent架构说明.md
---

# 中文Prompt Injection检测盲区

## 问题

Hermes的项目上下文安全扫描只覆盖英文模式，中文prompt injection（如"忽略之前的所有指令"）不在检测范围内。

## 影响

如果攻击者诱导Agent往.hermes.md里写中文恶意指令，每次启动都会触发永久后门，正则扫描完全检测不到。

## 讨论：正则 vs 模型

- **正则**：快，容易被绕过，检测模式固定
- **模型检测**：更鲁棒，但增加延迟和成本

## 开放问题

是否应该用模型来做injection检测而不是正则？成本和鲁棒性如何平衡？

## 相关链接

  - [[系统提示词工程]]
