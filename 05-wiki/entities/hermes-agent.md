---
id: hermes-agent
tags: [entity, agent, hermes]
created: 2026-04-27
source: 01-学习/ai学习/Hermes Agent架构说明.md
---

# Hermes Agent

开源AI Agent项目，两个月4.7万星。

## 核心定位

通用Agent框架，支持20+消息平台（飞书、钉钉、Telegram、Discord、Slack、WhatsApp、iMessage、Email、SMS等）。

## 五层架构

| 层级 | 职责 | 核心组件 |
|------|------|----------|
| 入口层 | 消息接收 | CLI + 20+平台适配器 |
| 网关层 | 连接与会话管理 | GatewayRunner |
| 执行层 | 推理与工具执行 | AIAgent (run_agent.py) |
| 扩展层 | 能力扩展 | 工具注册中心、技能系统、子Agent、MCP客户端、8个记忆Provider |
| 存储层 | 数据持久化 | SQLite+FTS5、MEMORY.md/USER.md、Skills目录、config.yaml |

## 消息完整路径

终端输入 → CLI解析 → 会话加载 → 上下文组装 → 模型推理 → 工具执行 → 流式输出 → 状态落盘

## 关键特性

- **Profile隔离**：通过HERMES_HOME环境变量实现多环境独立
- **迭代预算**：父Agent 90轮，子Agent 50轮，防止无限循环
- **PTC机制**：execute_code工具调用退还1次迭代预算
- **子Agent委托**：独立上下文，独立预算，级联中断
- **自进化**：后台每10轮推理触发技能复盘
