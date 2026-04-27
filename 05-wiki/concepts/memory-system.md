---
id: memory-system
tags: [concept, hermes, memory]
created: 2026-04-27
source: 01-学习/ai学习/Hermes Agent架构说明.md
---

# 记忆系统

Hermes的记忆是冻结快照 + 文件持久化 + 按需检索的组合。

## 两个记忆文件

- **MEMORY.md**：Agent自己的笔记（"这台机器Python是3.11"）
- **USER.md**：Agent对用户的了解（偏好、沟通风格）

## 字符限额

- MEMORY.md：2200字符
- USER.md：1375字符

按字符算而非token，模型无关，换模型不用重算。

## 冻结快照机制

会话开始时注入系统提示词，会话期间不再更新。

**设计目的**：每轮写记忆都改系统提示词 → 缓存无法命中。冻结快照用一致性换性能。

**数据不丢**：工具写入的记忆立即持久化到磁盘，下次新会话才刷新快照。

## 外部记忆Provider

可选8个：Honcho、Mem0、Hindsight、Holographic、ByteRover、OpenViking、RetainDB、Supermemory。

内置Provider永远在，外部同时只能开一个。

## 安全扫描

记忆写入也要过安全扫描（prompt injection/角色劫持/数据外泄等），防止永久后门。
