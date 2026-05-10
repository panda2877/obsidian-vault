# 生活助手 M1 — API 接口设计文档

> 作者：幸如音（技术专家）
> 日期：2026-05-10
> 项目：Hermes Dashboard — 生活助手模块

---

## 1. 概述

所有生活助手 API 前缀为 `/api/life/`，**除鉴权接口外均需 Token 验证**。

- **基础 URL**：`https://<host>:<port>/api/life/`
- **数据格式**：请求/响应均为 `application/json`
- **字符编码**：UTF-8

---

## 2. 状态码定义

| 状态码 | 含义 | 说明 |
|--------|------|------|
| `200` | 成功 | GET/PUT 操作成功 |
| `201` | 创建成功 | POST 操作成功 |
| `204` | 删除成功 | DELETE 操作成功（无响应体） |
| `400` | 请求参数错误 | 缺少必填字段、格式错误 |
| `401` | 未授权 | Token 缺失或无效 |
| `404` | 资源不存在 | 指定 ID 的记录不存在 |
| `409` | 冲突 | 设备已绑定等重复操作 |
| `429` | 请求过频 | 触发 rate limit |
| `500` | 服务器内部错误 | 数据库异常等 |

---

## 3. Token 鉴权中间件设计

### 3.1 鉴权流程

```
手机端 → 输入 LIFE_TOKEN → POST /api/life/auth/bind
  → 服务端验证 LIFE_TOKEN 是否匹配环境变量
  → 生成 JWT Token（有效期 365 天）+ 记录设备绑定
  → 返回 JWT Token

后续请求 → 携带 Authorization: Bearer <JWT>
  → 鉴权中间件验证 JWT 签名 + 有效期
  → 通过则放行，失败则 401
```

### 3.2 JWT 配置

| 参数 | 值 | 说明 |
|------|-----|------|
| 密钥 | `config.auth.jwtSecret` | 复用看板的 JWT Secret |
| 算法 | `HS256` | HMAC-SHA256 |
| 有效期 | `365 days` | 长效 Token，一年内无需重新登录 |
| Payload | `{ device_id, token_hash, iat, exp }` | 设备标识 + Token 哈希 |

### 3.3 中间件实现

```javascript
// backend/middleware/lifeAuth.js

const jwt = require('jsonwebtoken')
const config = require('../config')

/**
 * 生活助手 Token 鉴权中间件
 * 验证 Authorization header 中的 JWT
 * 通过后在 req.lifeDevice 中注入设备信息
 */
function lifeAuth(req, res, next) {
  const authHeader = req.headers.authorization || ''
  const token = authHeader.replace(/^Bearer\s+/i, '').trim()

  if (!token) {
    return res.status(401).json({ error: '缺少认证 Token', code: 'TOKEN_MISSING' })
  }

  try {
    const decoded = jwt.verify(token, config.auth.jwtSecret)
    req.lifeDevice = {
      deviceId: decoded.device_id,
      tokenHash: decoded.token_hash,
    }
    next()
  } catch (err) {
    if (err.name === 'TokenExpiredError') {
      return res.status(401).json({ error: 'Token 已过期，请重新绑定', code: 'TOKEN_EXPIRED' })
    }
    return res.status(401).json({ error: 'Token 无效', code: 'TOKEN_INVALID' })
  }
}

module.exports = lifeAuth
```

### 3.4 需要新增的依赖

在 `backend/package.json` 中新增：

```json
{
  "dependencies": {
    "jsonwebtoken": "^9.0.0"
  }
}
```

---

## 4. 鉴权接口

### 4.1 POST /api/life/auth/bind — 设备绑定

首次使用：输入 LIFE_TOKEN 完成设备绑定，获取 JWT。

**Request**：

```json
{
  "token": "用户输入的 LIFE_TOKEN",
  "device_id": "设备生成的 UUID（如：a1b2c3d4-...）",
  "device_name": "iPhone 15 Pro（可选）"
}
```

**成功响应 (200)**：

```json
{
  "success": true,
  "jwt": "eyJhbGciOiJIUzI1NiIs...",
  "expires_at": "2027-05-10T11:49:00.000Z",
  "message": "绑定成功"
}
```

**错误响应**：

| 状态码 | 条件 | 响应 |
|--------|------|------|
| `400` | 缺少 token 或 device_id | `{ "error": "缺少必填参数", "code": "MISSING_PARAMS" }` |
| `401` | LIFE_TOKEN 不匹配 | `{ "error": "Token 无效", "code": "TOKEN_MISMATCH" }` |
| `409` | 设备已绑定 | `{ "error": "该设备已绑定", "code": "DEVICE_ALREADY_BOUND" }` |

### 4.2 GET /api/life/auth/check — 验证 Token

验证当前 JWT 是否有效（前端启动时调用）。

**Headers**：

```
Authorization: Bearer <jwt>
```

**成功响应 (200)**：

```json
{
  "valid": true,
  "device_id": "a1b2c3d4-...",
  "bound_at": "2026-05-10T11:49:00.000Z"
}
```

**失败响应 (401)**：

```json
{
  "valid": false,
  "error": "Token 无效或已过期"
}
```

---

## 5. 记账接口

### 5.1 POST /api/life/finance — 新增记账

**Request**：

```json
{
  "type": "expense",
  "amount": 35.50,
  "category_id": 1,
  "note": "午餐 - 兰州拉面",
  "record_date": "2026-05-10"
}
```

**字段校验**：
- `type`：必须为 `income` 或 `expense`
- `amount`：必须 > 0
- `category_id`：必须存在且 type 匹配
- `record_date`：可选，默认当天

**成功响应 (201)**：

```json
{
  "success": true,
  "data": {
    "id": 42,
    "type": "expense",
    "amount": 35.50,
    "category_id": 1,
    "category_name": "餐饮",
    "note": "午餐 - 兰州拉面",
    "record_date": "2026-05-10",
    "created_at": "2026-05-10T12:00:00.000Z"
  }
}
```

### 5.2 GET /api/life/finance — 获取记账列表

**Query 参数**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `type` | string | 全部 | 筛选：`income` / `expense` |
| `category_id` | integer | 全部 | 按分类筛选 |
| `start_date` | string | 全部 | 开始日期 `YYYY-MM-DD` |
| `end_date` | string | 全部 | 结束日期 `YYYY-MM-DD` |
| `page` | integer | 1 | 页码 |
| `page_size` | integer | 20 | 每页条数（最大 100） |

**成功响应 (200)**：

```json
{
  "success": true,
  "data": [
    {
      "id": 42,
      "type": "expense",
      "amount": 35.50,
      "category_id": 1,
      "category_name": "餐饮",
      "category_icon": "🍜",
      "note": "午餐 - 兰州拉面",
      "record_date": "2026-05-10",
      "created_at": "2026-05-10T12:00:00.000Z",
      "updated_at": "2026-05-10T12:00:00.000Z"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 156,
    "total_pages": 8
  }
}
```

### 5.3 PUT /api/life/finance/:id — 修改记账

**Request**（仅传需要修改的字段）：

```json
{
  "amount": 38.00,
  "note": "午餐 - 兰州拉面（加蛋）"
}
```

**成功响应 (200)**：

```json
{
  "success": true,
  "data": { ... }  // 完整记录对象
}
```

### 5.4 DELETE /api/life/finance/:id — 删除记账

**成功响应 (204)**：无响应体。

**错误响应 (404)**：

```json
{
  "error": "记账记录不存在",
  "code": "RECORD_NOT_FOUND"
}
```

---

## 6. 分类接口

### 6.1 GET /api/life/categories — 获取分类列表

**Query 参数**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `type` | string | 全部 | 筛选：`income` / `expense` |

**成功响应 (200)**：

```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "餐饮",
      "type": "expense",
      "icon": "🍜",
      "sort_order": 1
    },
    {
      "id": 11,
      "name": "工资",
      "type": "income",
      "icon": "💰",
      "sort_order": 1
    }
  ]
}
```

---

## 7. 待办接口

### 7.1 POST /api/life/todo — 新增待办

**Request**：

```json
{
  "title": "买牛奶和面包",
  "description": "记得买全麦面包和低脂牛奶",
  "category": "shopping",
  "priority": "medium",
  "due_date": "2026-05-11"
}
```

**字段说明**：

| 字段 | 必填 | 类型 | 默认值 | 可选值 |
|------|------|------|--------|--------|
| `title` | ✅ | string | — | 1~200 字符 |
| `description` | ❌ | string | `""` | 可选 |
| `category` | ❌ | string | `"general"` | 自由标签 |
| `priority` | ❌ | string | `"medium"` | `low`, `medium`, `high`, `urgent` |
| `due_date` | ❌ | string | `null` | `YYYY-MM-DD` |

**成功响应 (201)**：

```json
{
  "success": true,
  "data": {
    "id": 7,
    "title": "买牛奶和面包",
    "description": "记得买全麦面包和低脂牛奶",
    "category": "shopping",
    "priority": "medium",
    "status": "pending",
    "due_date": "2026-05-11",
    "created_at": "2026-05-10T12:00:00.000Z",
    "updated_at": "2026-05-10T12:00:00.000Z"
  }
}
```

### 7.2 GET /api/life/todo — 获取待办列表

**Query 参数**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `status` | string | 全部 | `pending`, `in_progress`, `done`, `cancelled` |
| `priority` | string | 全部 | `low`, `medium`, `high`, `urgent` |
| `category` | string | 全部 | 分类标签 |
| `search` | string | 全部 | 标题/描述模糊搜索 |
| `page` | integer | 1 | 页码 |
| `page_size` | integer | 20 | 每页条数（最大 100） |

**排序规则**：默认按 `status` 排序（pending → in_progress → done → cancelled），同状态按 `priority` 排序（urgent → high → medium → low），同优先级按 `created_at DESC`。

**成功响应 (200)**：

```json
{
  "success": true,
  "data": [
    {
      "id": 7,
      "title": "买牛奶和面包",
      "description": "记得买全麦面包和低脂牛奶",
      "category": "shopping",
      "priority": "medium",
      "status": "pending",
      "due_date": "2026-05-11",
      "created_at": "2026-05-10T12:00:00.000Z",
      "updated_at": "2026-05-10T12:00:00.000Z"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 5,
    "total_pages": 1
  }
}
```

### 7.3 PUT /api/life/todo/:id — 更新待办

用于修改内容、变更状态（标记完成等）。

**Request**（仅传需要修改的字段）：

```json
{
  "status": "done",
  "priority": "high"
}
```

**成功响应 (200)**：返回完整任务对象。

### 7.4 DELETE /api/life/todo/:id — 删除待办

**成功响应 (204)**：无响应体。

---

## 8. 通用错误响应格式

所有接口在出错时遵循统一格式：

```json
{
  "error": "人类可读的错误描述",
  "code": "MACHINE_READABLE_CODE",
  "detail": "（可选）详细的技术信息"
}
```

### 错误码枚举

| Code | HTTP Status | 说明 |
|------|-------------|------|
| `TOKEN_MISSING` | 401 | 未携带 Token |
| `TOKEN_INVALID` | 401 | Token 格式/签名错误 |
| `TOKEN_EXPIRED` | 401 | Token 已过期 |
| `TOKEN_MISMATCH` | 401 | LIFE_TOKEN 不匹配 |
| `DEVICE_ALREADY_BOUND` | 409 | 设备已绑定 |
| `MISSING_PARAMS` | 400 | 缺少必填参数 |
| `INVALID_PARAMS` | 400 | 参数格式/值不合法 |
| `RECORD_NOT_FOUND` | 404 | 记录不存在 |
| `CATEGORY_NOT_FOUND` | 404 | 分类不存在 |
| `TYPE_MISMATCH` | 400 | 分类 type 与记录 type 不一致 |
| `INTERNAL_ERROR` | 500 | 服务器内部错误 |

---

## 9. 完整路由映射

```
POST   /api/life/auth/bind        → authController.bind
GET    /api/life/auth/check       → authController.check  [lifeAuth]

POST   /api/life/finance          → financeController.create  [lifeAuth]
GET    /api/life/finance          → financeController.list    [lifeAuth]
PUT    /api/life/finance/:id      → financeController.update  [lifeAuth]
DELETE /api/life/finance/:id      → financeController.delete  [lifeAuth]

GET    /api/life/categories       → categoryController.list   [lifeAuth]

POST   /api/life/todo             → todoController.create     [lifeAuth]
GET    /api/life/todo             → todoController.list       [lifeAuth]
PUT    /api/life/todo/:id         → todoController.update     [lifeAuth]
DELETE /api/life/todo/:id         → todoController.delete     [lifeAuth]
```

> 注：`auth/bind` 和 `auth/check` 无需 `lifeAuth` 中间件，`bind` 在验证 LIFE_TOKEN 后生成 JWT，`check` 自行验证 JWT。