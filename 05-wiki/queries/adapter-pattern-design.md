---
id: adapter-pattern-design
tags: [query, hermes, design]
created: 2026-04-27
source: 01-学习/ai学习/Hermes Agent架构说明.md
---

# 适配器模式设计取舍

## 问题

为什么Hermes的BasePlatformAdapter没有统一的抽象消息转换接口？

## 分析

各平台消息获取方式差异大（长轮询/WebSocket/IMAP/Webhook），统一抽象接口反而会束缚实现。

Hermes的选择：约定而不约束，各自监听、各自构造MessageEvent，后续代码全部对齐同一个内部对象。

## 结论

这是标准的适配器模式：进来时把外部差异统一成内部对象，出去时反向拆回各平台格式。

核心代码从头到尾只跟统一协议（MessageEvent）打交道，不用知道消息从哪来、要到哪去。想接新平台，写一个适配器就够。
