---
id: five-layer-architecture
tags: [concept, hermes, architecture]
created: 2026-04-27
source: 01-学习/ai学习/Hermes Agent架构说明.md
---

# 五层架构

Hermes Agent的整体架构分层。

## 各层职责

| 层级 | 职责 | 核心组件 |
|------|------|----------|
| 入口层 | 消息接收 | CLI + 20+平台适配器 |
| 网关层 | 连接与会话生命周期管理 | GatewayRunner（斜杠命令） |
| 执行层 | 组装上下文、调模型、跑工具、处理错误 | AIAgent (run_agent.py) |
| 扩展层 | 工具注册、技能系统、子Agent委托、MCP、记忆Provider | 工具注册中心、Skills系统 |
| 存储层 | 数据持久化 | SQLite+FTS5、MEMORY.md/USER.md、config.yaml、.env |

## 消息完整路径

终端输入 → CLI解析 → 会话加载 → 上下文组装 → 模型推理 → 工具执行 → 流式输出 → 状态落盘

## 相关链接

  - [[Hermes Agent]]
  - [[AIAgent主循环]]
  - [[记忆系统]]
