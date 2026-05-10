# 生活助手 M1 — API 接口设计补充文档（v0.8 原型改动）

> 作者：幸如音（技术专家）
> 日期：2026-05-10
> 项目：Hermes Dashboard — 生活助手模块
> 说明：本文档仅包含 v0.8 原型改动对应的新增/修改接口，与主文档 `life-api-design.md` 配合使用。

---

## 1. 新增接口

### 1.1 GET /api/life/finance/summary — 财务汇总接口

用于首页「本月支出」概览卡片的数据获取，返回当月收入总额、支出总额及较上月的变化百分比。

**鉴权**：需要 `lifeAuth` 中间件。

**Query 参数**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `start_date` | string | ❌ | 当月第一天 | 开始日期 `YYYY-MM-DD` |
| `end_date` | string | ❌ | 当月最后一天 | 结束日期 `YYYY-MM-DD` |

> 不传参时默认统计当前自然月的数据。

**SQL 逻辑**：

```sql
-- 当月支出总额
SELECT COALESCE(SUM(amount), 0) FROM finance_records
WHERE type = 'expense'
  AND record_date BETWEEN :start_date AND :end_date;

-- 当月收入总额
SELECT COALESCE(SUM(amount), 0) FROM finance_records
WHERE type = 'income'
  AND record_date BETWEEN :start_date AND :end_date;

-- 上月支出总额（用于计算变化百分比）
SELECT COALESCE(SUM(amount), 0) FROM finance_records
WHERE type = 'expense'
  AND record_date BETWEEN :prev_start AND :prev_end;

-- 上月收入总额（用于计算变化百分比）
SELECT COALESCE(SUM(amount), 0) FROM finance_records
WHERE type = 'income'
  AND record_date BETWEEN :prev_start AND :prev_end;
```

**变化百分比计算**：

```
change_percent = (本月总额 - 上月总额) / 上月总额 * 100
上月总额为 0 时，变化百分比为 0
```

**成功响应 (200)**：

```json
{
  "success": true,
  "data": {
    "income_total": 12580,
    "expense_total": 3260,
    "income_change": 8.2,
    "expense_change": -5.1
  }
}
```

**响应字段说明**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `income_total` | number | 当月收入总额（元） |
| `expense_total` | number | 当月支出总额（元） |
| `income_change` | number | 收入较上月变化百分比（正数=增长，负数=下降） |
| `expense_change` | number | 支出较上月变化百分比（正数=增长，负数=下降） |

**错误响应**：

| 状态码 | 条件 | 响应 |
|--------|------|------|
| `400` | 日期格式错误 | `{ "error": "日期格式无效，应为 YYYY-MM-DD", "code": "INVALID_PARAMS" }` |

---

### 1.2 GET /api/life/feed — 最近动态混合流接口

用于首页「最近动态」模块，从多个数据源（记账、待办等）获取最近记录，合并后按时间倒序返回。

**鉴权**：需要 `lifeAuth` 中间件。

**Query 参数**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `limit` | integer | ❌ | 20 | 返回条数（最大 50） |

**实现逻辑（M1 简化版）**：

1. 从 `finance_records` 取最近 10 条记录（按 `created_at DESC`）
2. 从 `todo_tasks` 取最近 10 条记录（按 `created_at DESC`）
3. 合并后按 `created_at DESC` 排序，取前 `limit` 条
4. 每条记录统一为 feed 条目格式

**SQL 逻辑**：

```sql
-- 取最近 10 条记账记录
SELECT
  'finance' AS type,
  f.note AS title,
  c.icon,
  c.name AS category_name,
  f.type AS amount_type,
  CASE WHEN f.type = 'expense' THEN -f.amount ELSE f.amount END AS amount,
  f.created_at AS time,
  f.record_date
FROM finance_records f
LEFT JOIN finance_categories c ON f.category_id = c.id
ORDER BY f.created_at DESC
LIMIT 10;

-- 取最近 10 条待办记录
SELECT
  'todo' AS type,
  t.title,
  '📋' AS icon,
  t.category AS category_name,
  NULL AS amount_type,
  NULL AS amount,
  t.created_at AS time,
  t.due_date,
  t.status,
  t.priority
FROM todo_tasks t
ORDER BY t.created_at DESC
LIMIT 10;
```

**成功响应 (200)**：

```json
{
  "success": true,
  "data": [
    {
      "type": "finance",
      "title": "午餐 - 兰州拉面",
      "meta": "餐饮 · 10分钟前",
      "icon": "🍜",
      "amount": -28,
      "amount_type": "expense"
    },
    {
      "type": "todo",
      "title": "买牛奶和面包",
      "meta": "待办 · 1小时前创建",
      "icon": "📋",
      "status": "pending"
    }
  ]
}
```

**响应字段说明**：

| 字段 | 类型 | 说明 | 适用类型 |
|------|------|------|----------|
| `type` | string | 数据来源类型：`finance` / `todo` | 全部 |
| `title` | string | 标题（finance 为备注内容，todo 为任务标题） | 全部 |
| `meta` | string | 人类可读的描述文本，格式：`"分类名 · 相对时间"` 或 `"待办 · 相对时间"` | 全部 |
| `icon` | string | Emoji 图标 | 全部 |
| `time` | string | ISO 8601 时间戳 | 全部 |
| `amount` | number | 金额（finance 专有，支出为负数） | `finance` |
| `amount_type` | string | 收支类型：`income` / `expense` | `finance` |
| `status` | string | 待办状态：`pending` / `in_progress` / `done` / `cancelled` | `todo` |
| `priority` | string | 待办优先级：`low` / `medium` / `high` / `urgent` | `todo` |
| `due_date` | string | 截止日期 `YYYY-MM-DD` | `todo` |

> **M1 阶段说明**：当前为简化实现，由后端分别查询后合并返回。后续 M2 阶段可改为前端分别请求各模块动态后自行合并，以支持分页和独立刷新。

---

## 2. 修改接口

### 2.1 GET /api/life/todo — 获取待办列表（参数扩展）

在原接口基础上新增排序和条数限制参数，以支持首页「紧急待办」模块的查询需求。

**新增 Query 参数**（加粗为新增）：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `status` | string | 全部 | `pending`, `in_progress`, `done`, `cancelled` |
| `priority` | string | 全部 | `low`, `medium`, `high`, `urgent` |
| `category` | string | 全部 | 分类标签 |
| `search` | string | 全部 | 标题/描述模糊搜索 |
| **`sort_by`** | string | `default` | 排序字段：`priority`, `due_date`, `created_at`, `default`（按原有规则） |
| **`sort_order`** | string | `asc` | 排序方向：`asc` / `desc` |
| **`limit`** | integer | 无限制 | 限制返回条数（最大 100） |
| `page` | integer | 1 | 页码（与 `limit` 互斥，当 `limit` 存在时分页参数失效） |
| `page_size` | integer | 20 | 每页条数（最大 100，与 `limit` 互斥） |

**排序规则说明**：

| `sort_by` 值 | 排序逻辑 | 典型场景 |
|-------------|----------|----------|
| `default` | 按原有规则：status → priority → created_at DESC | 待办列表页 |
| `priority` | 按优先级排序（配合 `sort_order=desc` 取最紧急的） | 紧急待办模块 |
| `due_date` | 按截止日期排序（配合 `sort_order=asc` 取快到期的） | 截止日期排序 |
| `created_at` | 按创建时间排序 | 最新创建排序 |

**优先级映射**（用于 `sort_by=priority` 排序）：

```
urgent = 0, high = 1, medium = 2, low = 3
```

**紧急待办查询示例**：

```
GET /api/life/todo?status=pending,in_progress&sort_by=priority&sort_order=desc&limit=3
```

对应 SQL：

```sql
SELECT * FROM todo_tasks
WHERE status IN ('pending', 'in_progress')
ORDER BY
  CASE priority
    WHEN 'urgent' THEN 0
    WHEN 'high'   THEN 1
    WHEN 'medium' THEN 2
    WHEN 'low'    THEN 3
  END ASC,
  due_date ASC
LIMIT 3;
```

**响应格式**（与原有接口一致，但无 `pagination` 字段当 `limit` 参数存在时）：

```json
{
  "success": true,
  "data": [
    {
      "id": 5,
      "title": "提交项目报告",
      "description": "周五前必须提交",
      "category": "work",
      "priority": "urgent",
      "status": "pending",
      "due_date": "2026-05-11",
      "created_at": "2026-05-10T08:00:00.000Z",
      "updated_at": "2026-05-10T08:00:00.000Z"
    }
  ]
}
```

> ⚠️ **注意**：当 `limit` 参数存在时，响应中不包含 `pagination` 对象（因为 LIMIT 模式不涉及分页）。当 `limit` 不存在时，按原有分页逻辑返回 `pagination`。

---

## 3. 路由映射更新

将新增和修改的路由加入主文档的完整路由映射中：

```diff
 POST   /api/life/auth/bind        → authController.bind
 GET    /api/life/auth/check       → authController.check  [lifeAuth]

 POST   /api/life/finance          → financeController.create  [lifeAuth]
 GET    /api/life/finance          → financeController.list    [lifeAuth]
+GET    /api/life/finance/summary  → financeController.summary [lifeAuth]  <!-- v0.8 新增 -->
 PUT    /api/life/finance/:id      → financeController.update  [lifeAuth]
 DELETE /api/life/finance/:id      → financeController.delete  [lifeAuth]

 GET    /api/life/categories       → categoryController.list   [lifeAuth]

 POST   /api/life/todo             → todoController.create     [lifeAuth]
-GET    /api/life/todo             → todoController.list       [lifeAuth]
+GET    /api/life/todo             → todoController.list       [lifeAuth]  <!-- v0.8 新增参数: sort_by, sort_order, limit -->
 PUT    /api/life/todo/:id         → todoController.update     [lifeAuth]
 DELETE /api/life/todo/:id         → todoController.delete     [lifeAuth]

+GET    /api/life/feed             → feedController.list       [lifeAuth]  <!-- v0.8 新增 -->
```

---

## 4. 新增错误码

| Code | HTTP Status | 说明 |
|------|-------------|------|
| `INVALID_SORT_FIELD` | 400 | sort_by 参数值不合法 |
| `INVALID_SORT_ORDER` | 400 | sort_order 参数值不合法（非 asc/desc） |
| `LIMIT_EXCEEDED` | 400 | limit 超过最大值 100 |