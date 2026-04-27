---
title: 飞书群聊 Inject Tool 技术方案
created: 2026-04-27
updated: 2026-04-27
type: concept
tags: [飞书, Hermes, Multi-Agent, Inject-Tool, 架构设计]
sources: []
related_docs: []
---

# 飞书群聊 Inject Tool 技术方案

- todo：确认一下，这个方案下，群里面的session数量

## 1. 问题背景

### 1.1 现状问题

飞书平台存在一个根本性限制：**Bot 无法看到其他 Bot 发送的消息**。在群聊场景下，当 Bot A 发送包含 `@Bot B` 的消息时，飞书不会向 Bot B 推送 `im.message.receive_v1` 事件，导致 Bot B 无法感知自己被 @。

在当前 Hermes Agent 的多姐妹架构下：

| 通信场景 | 现状 | 问题 |
|---------|------|------|
| 人在群里 @银月 | ✅ 银月能收到 | 正常 |
| 人在群里 @如音 | ✅ 如音能收到 | 正常 |
| 银月在群里 @如音 | ❌ 如音收不到 | 飞书 Bot@Bot 不推事件 |
| 如音在群里 @银月 | ❌ 银月收不到 | 飞书 Bot@Bot 不推事件 |

随着团队扩展（紫灵、思月等姐妹加入），需要在群聊中实现 Agent 之间的工作协同，这个限制成为核心障碍。

### 1.2 竞品参考

OpenClaw 项目通过**进程内拦截 + 合成事件**的方式成功解决了这一问题。其核心思路：

```
Bot A 的 AI 生成包含 @Bot B 的回复
  → reply-dispatcher 提取 <at> 标签
  → sendMessageFeishu 发送消息后，检测 mentions 中是否有 bot
  → triggerBotToBotMessage 构造合成 FeishuMessageEvent
  → 直接调用 Bot B 的 im.message.receive_v1 handler
  → Bot B 像收到真实消息一样处理并回复
```

但 Hermes 的架构与 OpenClaw 不同，需要适配性设计。

---

## 2. Hermes 架构约束分析

### 2.1 当前架构

Hermes Gateway 的平台配置采用 `Dict[Platform, PlatformConfig]` 结构，一个进程只能实例化一个特定 Platform 的 adapter（因为用 Platform enum 做 key）。因此：

- 银月的 Gateway 进程 → 持有银月的 Feishu Adapter（cli_xxx银月）
- 如音的 Gateway 进程 → 持有如音的 Feishu Adapter（cli_a965e85a6f4b9bdd）
- 两个进程完全独立，Feishu 分别推送给各自的 Gateway

### 2.2 架构约束

| 约束项 | 说明 |
|-------|------|
| 多 Bot 必须多进程 | 每个飞书 Bot 需要独立的 Gateway 进程 |
| 进程间无共享状态 | 各 Gateway 进程内存隔离 |
| 飞书事件分发 | 飞书只把消息推给对应 Bot 的 WebSocket 连接 |
| 无法进程内拦截 | 银月和如音的 Gateway 不在同一进程，无法像 OpenClaw 那样直接调用对方的 handler |

### 2.3 结论

OpenClaw 的「进程内拦截」方案在 Hermes 中不可直接复用。需要引入**进程间通信机制**来模拟 Bot@Bot 消息注入。

---

## 3. 解决方案总体设计

### 3.1 核心思路

不依赖飞书平台的 Bot@Bot 事件推送，而是引入**主动轮询 + 注入**机制：

```
┌─────────────────────────────────────────────────────────────┐
│                    飞书群（oc_08a798e...）                    │
│  [User] [@银月] [@如音] [@紫灵]                                │
└─────────────────────────────────────────────────────────────┘
         ▲                  ▲                  ▲
         │                  │                  │
         │         Polling Relay Service        │
         │    （每 N 秒轮询群消息，主动拉取）     │
         │                  │                  │
         │    ┌─────────────┼─────────────┐    │
         │    ▼             ▼             ▼    │
    ┌─────────┐      ┌─────────┐    ┌─────────┐
    │ inject  │      │ inject  │    │ inject  │
    │ tool    │      │ tool    │    │ tool    │
    └────┬────┘      └────┬────┘    └────┬────┘
         │                 │                 │
    ┌────┴────┐      ┌────┴────┐     ┌────┴────┐
    │银月 GW  │      │如音 GW  │     │紫灵 GW  │
    │进程     │      │进程     │     │进程     │
    └─────────┘      └─────────┘     └─────────┘
```

### 3.2 轮询 Relay Service

**职责**：
1. 持续调用飞书 `im/v1/messages` API 拉取群消息（轮询间隔建议 3-5 秒）
2. 检测新消息中是否有 @指定Bot 的内容
3. 将消息通过 HTTP POST 分发给对应 Bot 的 Gateway inject tool

**关键设计**：Relay Service **只负责轮询和分发**，不处理任何业务逻辑。它不知道自己分发了什么，只负责「把 A 的消息交给 B」。

### 3.3 Inject Tool（标准扩展点）

**定位**：Inject Tool 是 Hermes Gateway 的标准扩展点，所有姐妹的 Gateway 天然自带此能力，不需要各自单独开发。

**接口设计**：

```
POST /inject
Content-Type: application/json

{
  "platform": "feishu",
  "chat_id": "oc_08a798e06860c6b905f8090aec40208b",
  "message": "@银月 帮我看下如音的工作进度",
  "sender": {
    "user_id": "ou_xxxxx",
    "name": "幸如音"
  },
  "mentioned_bots": ["@银月"],
  "raw_event": { ... }  // 原始飞书事件，用于 session 追踪
}
```

**响应**：
```json
{
  "status": "delivered",
  "session_id": "agent:main:feishu:group:oc_08a798e...:on_xxxxx"
}
```

**安全设计**：
- Relay Service 调用 inject tool 时需要携带共享密钥（`INJECT_SHARED_SECRET`）
- Gateway 验证密钥后才处理注入请求
- 密钥在各姐妹 profile 的 .env 中配置

---

## 4. 自动发现注册机制

### 4.1 问题

如果 Relay Service 硬编码「@银月 → 银月的inject URL」映射，每次加新姐妹都要改 Relay 代码和配置。

### 4.2 解决方案：注册中心

```
┌─────────────────────────────────────────────────────┐
│                   Relay Service                       │
│  ┌───────────────────────────────────────────────┐   │
│  │            Bot Registry（内存/持久化）          │   │
│  │  @银月   → {inject_url, gateway_pid, status} │   │
│  │  @如音   → {inject_url, gateway_pid, status} │   │
│  │  @紫灵   → {inject_url, gateway_pid, status} │   │
│  └───────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
                          ▲
                          │ self-register
                          │
    各姐妹 Gateway 启动时 → POST /register
```

**注册接口**：

```
POST /register
{
  "bot_mention": "@银月",
  "inject_url": "http://localhost:9119/inject",
  "gateway_pid": 12345,
  "profile": "yinyue"
}
```

**心跳保活**：各姐妹 Gateway 每 60 秒向 Relay 发送一次心跳，超过 120 秒无心跳则标记为离线。

### 4.3 新姐妹加入流程（零配置）

```
1. 在自己的 profile .env 中添加一行：
   FEISHU_BOT_MENTION=@紫灵
   FEISHU_INJECT_URL=http://localhost:9119/inject
   INJECT_SHARED_SECRET=xxxxx

2. 启动 Gateway

3. Gateway 启动时自动调用 Relay 的 /register 接口注册

4. 完成！Relay 自动知道 @紫灵 → 紫灵的 inject URL
```

**优点**：
- ✅ 新姐妹加入零配置变更（不改 Relay 代码）
- ✅ 各姐妹独立，不互相影响
- ✅ O(1) 复杂度：加姐妹只有新增，无修改

---

## 5. Inject Tool 在 Hermes Gateway 中的实现

### 5.1 实现位置

`gateway/platforms/feishu.py` 中的 `FeishuAdapter` 类，新增一个 HTTP 端点：

```python
# 在 FeishuAdapter.__init__ 中注册路由
self._router.add_route("POST", "/inject", self._handle_inject)

async def _handle_inject(self, request):
    """接收来自 Relay Service 的消息注入"""
    # 1. 验证 shared secret
    # 2. 解析请求体
    # 3. 构造 FeishuMessageEvent 对象
    # 4. 调用原有的消息处理流程 self._on_p2p_message / self._on_group_message
    # 5. 返回 deliver status
```

### 5.2 关键点

| 要点 | 说明 |
|------|------|
| **不做修改，只扩展** | 不改动原有 `on_message` 逻辑，新增 `/inject` handler 复用原有处理流程 |
| **验证 shared secret** | 防止恶意注入 |
| **复用 session** | 注入消息走原有 session 管理，保证上下文连续性 |
| **幂等处理** | 依赖飞书 message_id 做去重，避免重复注入 |

### 5.3 消息注入后的处理流程

```
Relay Service 调用 inject tool
  → _handle_inject 验证 secret
  → 构造 FeishuMessageEvent（模拟飞书推过来的事件）
  → 调用 _dispatch_inbound_message
  → 触发原有消息处理流程
  → 进入 Agent 主循环
  → 生成回复
```

---

## 6. 各姐妹 Gateway 配置

### 6.1 新增环境变量

| 变量名 | 说明 | 示例 |
|-------|------|------|
| `FEISHU_BOT_MENTION` | 机器人在群里的 @别名 | `@银月` |
| `FEISHU_INJECT_URL` | 自身 Gateway 的 inject 端点 | `http://localhost:9119/inject` |
| `FEISHU_RELAY_URL` | Relay Service 的地址 | `http://localhost:9120` |
| `INJECT_SHARED_SECRET` | 与 Relay 共享的密钥 | `xxxxx` |

### 6.2 银月配置示例（~/.hermes/.env）

```bash
# 已有配置
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx
FEISHU_BOT_MENTION=@银月
FEISHU_INJECT_URL=http://localhost:9119/inject
FEISHU_RELAY_URL=http://localhost:9120
INJECT_SHARED_SECRET=hermes-inject-secret-2026
```

### 6.3 如音配置示例（~/.hermes/profiles/xingruyin/.env）

```bash
# 已有配置
FEISHU_APP_ID=cli_a965e85a6f4b9bdd
FEISHU_APP_SECRET=xxx
FEISHU_GROUP_POLICY=open
# 新增配置
FEISHU_BOT_MENTION=@幸如音
FEISHU_INJECT_URL=http://localhost:9119/inject
FEISHU_RELAY_URL=http://localhost:9120
INJECT_SHARED_SECRET=hermes-inject-secret-2026
```

### 6.4 紫灵配置示例（未来）

```bash
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx
FEISHU_BOT_MENTION=@紫灵
FEISHU_INJECT_URL=http://localhost:9119/inject
FEISHU_RELAY_URL=http://localhost:9120
INJECT_SHARED_SECRET=hermes-inject-secret-2026
```

---

## 7. 完整消息流

### 7.1 人在群里 @银月（现有流程，不变）

```
人在群里发 @银月 xxx
  → 飞书推送 event 给银月的 Gateway
  → _on_group_message 处理
  → 银月回复
```

### 7.2 如音在群里 @银月（新增流程）

```
如音在群里发 @银月 xxx
  → 飞书推 event 给如音的 Gateway（如音能收到，因为是人在 @她）
  → 如音回复群聊（但银月看不到，因为飞书不推 Bot@Bot 事件）
  ↓
Relay Service 每 5 秒轮询
  → 拉到如音发的消息（含 @银月）
  → 查询注册表：@银月 → 银月的 inject URL
  → POST http://银月-gateway:9119/inject
  → 银月的 Gateway 收到注入请求
  → 走原有消息处理流程
  → 银月生成回复
  → 银月回复群聊
```

### 7.3 银月在群里 @如音（新增流程）

```
银月在群里发 @幸如音 xxx
  → 飞书推 event 给银月的 Gateway（银月能收到）
  → 银月回复群聊
  ↓
Relay Service 轮询
  → 拉到银月发的消息（含 @幸如音）
  → 查询注册表：@幸如音 → 如音的 inject URL
  → POST http://如音-gateway:9119/inject
  → 如音的 Gateway 收到注入请求
  → 如音生成回复
  → 如音回复群聊
```

---

## 8. 实现步骤

### Phase 1：Hermes Gateway Inject Tool（由如音姐姐负责）

- [ ] 在 `FeishuAdapter` 中新增 `/inject` HTTP 端点
- [ ] 实现 `_handle_inject` 方法，复用原有消息处理流程
- [ ] 添加 `INJECT_SHARED_SECRET` 验证
- [ ] 确保幂等（基于 message_id 去重）
- [ ] 单元测试

### Phase 2：Relay Service（由如音姐姐负责）

- [ ] 新建 `relay_service/` 目录
- [ ] 实现飞书 `im/v1/messages` API 轮询
- [ ] 实现 Bot Registry（注册表）
- [ ] 实现 `/register` 注册接口 + 心跳机制
- [ ] 实现 `/inject` 分发逻辑
- [ ] 部署脚本和 systemd service

### Phase 3：集成与测试

- [ ] 银月的 Gateway 接入 Relay，完成端到端测试
- [ ] 如音的 Gateway 接入 Relay，完成 Bot@Bot 互相通信测试
- [ ] 验证消息上下文连续性
- [ ] 性能测试（轮询延迟、并发 injection）

### Phase 4：文档与归档

- [ ] 更新各姐妹 profile 配置示例
- [ ] 编写运维手册（启动、重启、监控）
- [ ] 归档本文档

---

## 9. 监控与运维

### 9.1 Relay Service 监控

| 指标 | 说明 |
|------|------|
| 轮询延迟 | 从消息发送到被 injection 的时间差 |
| 注册表大小 | 当前在线的 Bot 数量 |
| injection 成功率 | 多少 % 的 injection 成功送达 |
| 心跳存活 | 各 Bot 是否在 线 |

### 9.2 日志

- Relay Service 日志：`/var/log/hermes/relay-service.log`
- 各 Gateway inject 日志：复用原有 gateway 日志

### 9.3 故障处理

| 故障场景 | 处理方式 |
|---------|---------|
| Relay Service 挂了 | 重启 systemd，Bot@Bot 通信暂停，但人与 Bot 通信不受影响 |
| 某 Bot Gateway 挂了 | Relay 心跳超时，标记离线，消息暂存重试队列 |
| injection 失败 | HTTP 429/5xx → 指数退避重试，最多 3 次 |

---

## 10. 总结

| 项目 | 说明 |
|------|------|
| **问题** | 飞书 Bot@Bot 消息不触发事件，多 Agent 群聊协作受阻 |
| **方案** | 引入 Polling Relay Service + Inject Tool 标准扩展点 |
| **改动范围** | Hermes Gateway 加 inject 端点（不做修改）+ Relay Service（新建）+ 各 profile 加配置 |
| **扩展性** | 新姐妹只需在 profile 加配置，自动注册，无需改 Relay 代码 |
| **安全性** | Shared Secret 验证 + 幂等处理 |
| **容错性** | 指数退避重试 + 心跳保活 |

---

*本文档由银月编写，用于记录飞书群聊 Inject Tool 技术方案*
*待如音姐姐评审并出具技术实现细节*
*最后更新：2026-04-27 银月*
