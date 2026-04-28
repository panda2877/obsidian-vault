# Code-Plan 用量监控系统 · 技术方案

**状态**：v0.2（基于 Hermes Workspace 官方 API 架构）
**需求来源**：银月转达
**目标**：最小化 API 调用消耗，实现精准用量监控与提前预警

---

## 1. 需求拆解

| 指标 | 值 |
|------|-----|
| 分段时间统计 | 6 段 × 600次/段 = 3600次 |
| 每周统计 | 6000 次 |
| 预警阈值 | 余量 < 5% 时提醒 |
| 核心约束 | **零或最小化 API 调用消耗** |

> "零消耗"意味着**不在常规调用路径中触发外部 API 查询**，而是通过本地代理计数 + 定期对账同步实现。

---

## 2. 核心架构设计

### 2.1 计数机制：本地代理拦截（零 API 消耗）

```
用户请求
  ↓
[Hermes Gateway / 本地中间件]
  ↓（正常转发到 AI Provider）
  ↓
[Code-Plan Counter] ← 在此处拦截计数（内存 + 持久化）
  ↓
实际 AI Provider 请求 → 响应
```

**关键设计**：计数行为发生在请求**通过本地网关时**，不产生额外外部 API 调用。

### 2.2 数据存储结构

```typescript
// 存储位置：本地 SQLite 或 JSON 文件
// 使用 Hermes Workspace 已有的 session/profile 结构

interface CodePlanUsage {
  profile: string
  timeSlotIndex: number        // 0-5（6段）
  periodStart: number           // 时间段开始时间戳（Unix ms）
  count: number                 // 本段已用次数
  lastUpdated: number           // 最后更新时间
  weekTotal: number            // 本周累计（跨段累加）
  weekStart: number            // 本周开始时间戳
}

interface CodePlanAlert {
  profile: string
  threshold: number            // 触发阈值（如 0.05 = 5%）
  alertedAt: number | null     // 已提醒时间（防止重复提醒）
  slotIndex: number            // 哪个时间段触发了预警
  remaining: number            // 当时剩余次数
}
```

**存储选择**：
- 开发/轻量：JSON 文件（`~/.hermes/code-plan-usage.json`）
- 生产：SQLite（Hermes 已有 `better-sqlite3` 依赖）

### 2.3 分段时间槽设计

```
一周 = 7 天
每段 = 7 天 ÷ 6 段 ≈ 1.167 天/段

实际实现（按自然周对齐）：

| 槽位 | 时间范围（每周重复）      | 最大次数 |
|------|------------------------|---------|
| 0    | 周一 00:00 → 周二 04:00 | 600     |
| 1    | 周二 04:00 → 周三 08:00 | 600     |
| 2    | 周三 08:00 → 周四 12:00 | 600     |
| 3    | 周四 12:00 → 周五 16:00 | 600     |
| 4    | 周五 16:00 → 周六 20:00 | 600     |
| 5    | 周六 20:00 → 周日 23:59 | 600     |

每周总计 = 600 × 6 = 3600 次
（与 6000 次/周 的需求关系：3600 是"平滑限额"，6000 是绝对上限）
```

**注意**：6 段 × 600 = 3600，但需求提到"每周统计 6000 次"。两种解读：
1. **解读A**：每段 600 次是建议节奏控制，6000 是硬上限（超量仍放行但不推荐）
2. **解读B**：6000 = 6 × 1000（即更宽松的均分）

**建议采用解读A**：6 段用于展示"平稳消耗"，6000 作为总警戒线（当周累计超 6000 时触发强提醒）。

---

## 3. 核心算法

### 3.1 时间槽计算

```typescript
function getCurrentSlotIndex(): number {
  const now = Date.now()
  const weekStart = getWeekStart(now)  // 最近周一 00:00:00
  const elapsed = now - weekStart
  const totalMsInWeek = 7 * 24 * 60 * 60 * 1000
  const slotDuration = totalMsInWeek / 6
  return Math.min(5, Math.floor(elapsed / slotDuration))
}

function getWeekStart(timestamp: number): number {
  const d = new Date(timestamp)
  const day = d.getDay()  // 0=周日
  const diff = d.getDate() - day + (day === 0 ? -6 : 1)  // 调整到周一
  d.setDate(diff)
  d.setHours(0, 0, 0, 0)
  return d.getTime()
}
```

### 3.2 计数增量（零 API 消耗）

```typescript
function incrementUsage(profile: string, delta = 1): CodePlanUsage {
  const now = Date.now()
  const slotIndex = getCurrentSlotIndex()
  const weekStart = getWeekStart(now)

  const storage = loadStorage()  // SQLite 或 JSON
  
  const record = storage[profile] ?? createFreshRecord(profile, weekStart)
  
  // 周切换检测 → 重置所有计数器
  if (record.weekStart !== weekStart) {
    record.weekStart = weekStart
    record.weekTotal = 0
    record.count = 0
    record.timeSlotIndex = slotIndex
    record.lastUpdated = now
    record.periodStart = getSlotStart(now, slotIndex)
  }
  
  // 槽切换检测 → 重置当前槽计数器
  if (record.timeSlotIndex !== slotIndex) {
    record.count = 0
    record.timeSlotIndex = slotIndex
    record.periodStart = getSlotStart(now, slotIndex)
  }
  
  record.count += delta
  record.weekTotal += delta
  record.lastUpdated = now
  
  saveStorage(storage)
  return record
}
```

### 3.3 余量计算

```typescript
const SLOT_LIMIT = 600
const WEEK_LIMIT = 6000
const ALERT_THRESHOLD = 0.05  // 5%

function getRemaining(profile: string): { slot: number; week: number; slotPct: number; weekPct: number } {
  const record = loadStorage()[profile]
  if (!record) return { slot: SLOT_LIMIT, week: WEEK_LIMIT, slotPct: 1, weekPct: 1 }
  
  const slotRemaining = Math.max(0, SLOT_LIMIT - record.count)
  const weekRemaining = Math.max(0, WEEK_LIMIT - record.weekTotal)
  
  return {
    slot: slotRemaining,
    week: weekRemaining,
    slotPct: slotRemaining / SLOT_LIMIT,
    weekPct: weekRemaining / WEEK_LIMIT,
  }
}
```

### 3.4 预警判定

```typescript
function shouldAlert(profile: string): { alert: boolean; reason: string; remaining: number } {
  const { slot, week, slotPct, weekPct } = getRemaining(profile)
  const record = loadStorage()[profile]
  
  // 防止重复提醒：上次提醒后消耗超过 50 次才重新提醒
  const lastAlerted = record?.alertState?.lastAlertedAt ?? 0
  const sinceLastAlert = record.weekTotal - (record?.alertState?.alertedWeekTotal ?? 0)
  
  if (slotPct < ALERT_THRESHOLD && sinceLastAlert > 50) {
    return {
      alert: true,
      reason: `时间段余量不足5%（剩余 ${slot} 次）`,
      remaining: slot,
    }
  }
  
  if (weekPct < ALERT_THRESHOLD && sinceLastAlert > 50) {
    return {
      alert: true,
      reason: `本周余量不足5%（剩余 ${week} 次）`,
      remaining: week,
    }
  }
  
  return { alert: false, reason: '', remaining: 0 }
}
```

---

## 4. 最小化 API 消耗策略

### 4.0 官方 API 利用（核心更新）

**Hermes Workspace 已有的官方用量 API：**

| API | 端点 | 用途 | 是否计入会话限制 |
|-----|------|------|--------------|
| `sessions.usage` | Gateway RPC（WebSocket） | 单会话用量（已列入 slowRpcs 白名单） | 否 |
| `sessions.costs` | Gateway RPC（WebSocket） | 单会话成本 | 否 |
| `usage.analytics` | Gateway RPC（WebSocket） | 用量分析 | 否 |
| `usage.summary` | Gateway RPC（WebSocket） | 用量汇总 | 否 |
| `GET /api/analytics/usage` | Dashboard HTTP | 历史用量统计 | 否 |
| `GET /api/sessions` | Dashboard HTTP | 会话列表（含 input/output_tokens） | 否 |

**白名单保护**：`sessions.usage` 等 4 个 RPC 已被加入 slowRpcs 白名单，不会触发熔断，适合定期对账。

### 4.1 计数机制：本地拦截 + 官方 API 对账

```
用户请求
  ↓
[Hermes Gateway] → 拦截点：每次 chat 请求 +1 计数（内存 + 异步写盘）
  ↓（正常转发）
  ↓
AI Provider 响应
```

**每 30 分钟后台任务：**
1. 调用 `GET /api/sessions` 拉取会话列表（含 input_tokens / output_tokens）
2. 从 `DashboardSession.input_tokens + output_tokens` 推算调用次数
3. 与本地计数器对比，差异超过阈值（如 ±5%）→ 修正本地记录并告警

> **不增加额外 API 消耗**：`sessions.usage` / `sessions.costs` 等 4 个 RPC 已列入 slowRpcs 白名单，不触发熔断。

### 4.2 触发式 vs 轮询式

| 方案 | API 消耗 | 实时性 | 推荐 |
|------|---------|--------|------|
| 轮询 Provider API | 高 | 准实时 | ❌ |
| **本地拦截计数** | **零** | **实时** | **✓** |
| WebSocket 推送（Provider 支持） | 低 | 实时 | 备选 |

### 4.3 计数不阻塞

所有计数操作必须是**异步写盘**，不阻塞实际请求响应。

---

## 5. 提醒机制

### 5.1 提醒渠道

```
WeChat/Weixin 推送（通过 Hermes 已有平台集成）
  ↓
[Alert] code-plan 预警 · nous
余量不足5%（本周剩余 287 次，距离下周一还有 2 天）
时间：2026-04-26 20:48
```

### 5.2 提醒去重

```
状态机：
  余量 < 5% 且未提醒 → 发送提醒 → 记录 alertedAt
  已提醒后消耗超过 50 次 → 重新提醒
  消耗补充（如充值）→ 重置提醒状态
```

---

## 6. 实现位置

在 Hermes Workspace 中的建议实现路径：

```
hermes-workspace/
├── src/
│   ├── server/
│   │   ├── code-plan-usage.ts      # 核心计数逻辑（中间件）
│   │   ├── code-plan-storage.ts    # SQLite 持久化（复用 better-sqlite3）
│   │   ├── code-plan-alerts.ts     # 预警判定 + 推送（复用 weixin.ts）
│   │   └── code-plan-cron.ts       # 定期对账任务（每30分钟）
│   ├── routes/api/
│   │   ├── code-plan-status.ts     # GET /api/code-plan/status → 前端展示
│   │   └── code-plan-ack.ts        # POST /api/code-plan/ack → 用户确认
│   └── stores/
│       └── code-plan-store.ts      # 前端 Zustand store
```

**复用的已有基础设施（已验证）：**
- `src/server/gateway.ts` — WebSocket 连接，slowRpcs 白名单保护
- `src/server/hermes-dashboard-api.ts` — `getAnalytics()`, `listSessions()` 等 HTTP API
- `src/components/usage-meter/usage-meter.tsx` — 已有 UsageMeter 组件，可复用
- `src/server/hermes-api.ts` — Hermes FastAPI 客户端（listSessions / getSession）
- `platforms/weixin.ts` — WeChat 推送通道（已有）
- `better-sqlite3` — 数据持久化（已有 session 存储依赖）
- 定时任务框架（cron-manager 已有 CronJob 类型）

**对账复用代码示例：**
```typescript
import { listSessions } from '@/server/hermes-dashboard-api'
import { getAnalytics } from '@/server/hermes-dashboard-api'

// 每 30 分钟：拉取官方数据做对账
const sessions = await listSessions(100, 0)
const totalCalls = sessions.reduce((sum, s) => {
  const tokens = (s.input_tokens ?? 0) + (s.output_tokens ?? 0)
  return sum + Math.ceil(tokens / 1000) // 估算每 1k tokens ≈ 1 次调用
}, 0)
```

---

## 7. API 设计

### GET /api/code-plan/status

```json
{
  "ok": true,
  "profile": "nous",
  "slot": {
    "index": 2,
    "limit": 600,
    "used": 347,
    "remaining": 253,
    "pct": 0.422
  },
  "week": {
    "limit": 6000,
    "used": 1847,
    "remaining": 4153,
    "pct": 0.692
  },
  "alert": {
    "active": false,
    "message": null
  },
  "nextReset": "2026-05-04T00:00:00Z"
}
```

### GET /api/code-plan/status (当预警触发时)

```json
{
  "ok": true,
  "profile": "nous",
  "slot": { "index": 4, "limit": 600, "used": 589, "remaining": 11, "pct": 0.018 },
  "week": { "limit": 6000, "used": 5780, "remaining": 220, "pct": 0.037 },
  "alert": {
    "active": true,
    "message": "本周余量不足5%（剩余 220 次，距离下周一还有 1 天）",
    "remaining": 220
  },
  "nextReset": "2026-05-04T00:00:00Z"
}
```

---

## 8. 前端展示建议

### 8.1 状态条

```
[████████░░░░░░] 347/600 · 本周 1847/6000
```

### 8.2 颜色语义

| 剩余比例 | 颜色 |
|---------|------|
| > 30% | 绿色 |
| 10%~30% | 黄色 |
| < 10% | 红色（闪烁） |
| < 5% | 红色 + 弹窗提醒 |

---

## 9. 关键设计原则

1. **零主路径 API 消耗**：计数发生在本地网关中间件，不对外发起请求查询
2. **定期对账**：后台任务做增量同步，不影响主流程
3. **容错性**：本地计数损坏时，可从 Provider API 完整恢复
4. **无状态热更新**：计数逻辑重启后读盘即恢复
5. **预警去重**：防止狂轰滥炸提醒

---

## 10. 开放问题（待确认）

1. **600 次/段是建议值还是硬上限？**（超量时是否拒绝请求？）
2. **多 profile 间是否共享 quota？**（如果是，需要聚合计算）
3. **提醒渠道优先级？**（WeChat > Email > 站内信？）
4. **6000 次/周是针对单个模型还是所有模型？**
5. **对账估算精度**：以 tokens 估算调用次数存在误差，是否有更精确的官方计数？

---

*方案版本：v0.2 · 基于 Hermes Workspace 官方 API（sessions.usage/slowRpcs/dashboard HTTP）更新 · 待如音确认后细化实现细节*
