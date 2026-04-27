---
id: base-platform-adapter
tags: [entity, hermes, pattern]
created: 2026-04-27
source: 01-学习/ai学习/Hermes Agent架构说明.md
---

# BasePlatformAdapter

Hermes平台适配器基类。

## 定义



## 设计特点

- **约定优于约束**：各平台适配器在connect()里自己构造MessageEvent，没有统一的抽象接口
- **消息转换内嵌**：各平台差异（长轮询/WebSocket/IMAP/Webhook）自行处理
- **一进一出**：进来统一成MessageEvent，出去反向拆回各平台格式

## 典型适配器

- Telegram：长轮询
- Slack：WebSocket
- Email：IMAP
- SMS：Twilio HTTP Webhook

## 相关链接

  - [[适配器模式设计取舍]]
