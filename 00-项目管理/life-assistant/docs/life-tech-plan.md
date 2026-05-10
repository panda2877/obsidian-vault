# 生活助手 M1 — 技术方案概述

> 作者：幸如音（技术专家）
> 日期：2026-05-10
> 项目：Hermes Dashboard — 生活助手模块

---

## 1. 目录结构说明

### 1.1 后端新增/修改文件

```
backend/
├── server.js                          # [修改] 启动时调用 lifeInitDb()
├── config.js                          # [修改] 新增 life.token 配置项
├── package.json                       # [修改] 新增 jsonwebtoken 依赖
├── middleware/
│   └── lifeAuth.js                    # [新增] JWT 鉴权中间件
├── services/
│   └── lifeDb.js                      # [新增] 生活助手数据库初始化 + CRUD 操作
├── controllers/
│   ├── lifeAuthController.js          # [新增] 鉴权控制器
│   ├── lifeFinanceController.js       # [新增] 记账控制器
│   ├── lifeCategoryController.js      # [新增] 分类控制器
│   └── lifeTodoController.js          # [新增] 待办控制器
└── routes/
    └── life.js                        # [重写] 替换为生活助手 CRUD 路由
```

### 1.2 前端新增/修改文件

```
src/
├── pages.json                         # [已有] 已配置 life 路由 + TabBar
├── pages/life/
│   ├── life.vue                       # [重写] 生活助手主页面（Tab 入口）
│   ├── finance.vue                    # [新增] 记账页面
│   ├── finance-add.vue                # [新增] 新增/编辑记账
│   ├── todo.vue                       # [新增] 待办列表页面
│   ├── todo-add.vue                   # [新增] 新增/编辑待办
│   └── auth.vue                       # [新增] Token 绑定页面（首次使用）
├── api/
│   └── life.js                        # [新增] 生活助手 API 封装（uni.request）
├── stores/
│   └── life.js                        # [新增] Pinia 状态管理（Token、记账、待办）
└── static/icons/
    ├── life.svg                       # [已有] TabBar 图标
    └── life-active.svg                # [已有] TabBar 选中图标
```

---

## 2. 实现步骤

### 第一阶段：后端基础设施（优先级 P0）

#### Step 1: 安装依赖
```bash
cd /home/agentuser/public/hermes-dashboard/backend
npm install jsonwebtoken
```

#### Step 2: 新增配置项
在 `backend/config.js` 中新增：
```javascript
life: {
  token: process.env.LIFE_TOKEN || 'life-default-token-2026',
}
```

#### Step 3: 创建鉴权中间件
新建 `backend/middleware/lifeAuth.js`，实现 JWT 验证逻辑（详见 API 文档 §3.3）。

#### Step 4: 创建数据库服务
新建 `backend/services/lifeDb.js`，实现：
- `lifeInitDb()` — 建表 + 插入预设分类
- 各表的 CRUD 函数（`createFinanceRecord`, `listFinanceRecords`, `updateFinanceRecord`, `deleteFinanceRecord` 等）
- 分页查询 + 条件筛选逻辑

#### Step 5: 创建控制器
新建 4 个控制器文件，处理请求参数校验、调用 DB 服务、组装响应。

#### Step 6: 重写路由
重写 `backend/routes/life.js`，挂载所有新路由，应用 `lifeAuth` 中间件。

#### Step 7: 修改 server.js
在 `start()` 函数的 `sqlite.initDb()` 之后调用 `lifeInitDb()`。

### 第二阶段：前端核心功能（优先级 P0）

#### Step 8: 创建 API 封装
新建 `src/api/life.js`，封装所有生活助手接口调用：

```javascript
// 示例：记账 API
export const financeApi = {
  create(data) { return uni.request({ url: '/api/life/finance', method: 'POST', data }) },
  list(params) { return uni.request({ url: '/api/life/finance', method: 'GET', data: params }) },
  update(id, data) { return uni.request({ url: `/api/life/finance/${id}`, method: 'PUT', data }) },
  delete(id) { return uni.request({ url: `/api/life/finance/${id}`, method: 'DELETE' }) },
}
```

#### Step 9: 创建状态管理
新建 `src/stores/life.js`（Pinia），管理：
- `jwt` — 当前 JWT Token（持久化到 localStorage）
- `deviceId` — 设备 ID
- `isBound` — 是否已绑定
- `financeRecords` — 记账列表
- `todoTasks` — 待办列表
- `categories` — 分类列表

#### Step 10: 重写 life.vue
将占位页面改为功能入口页，包含：
- 顶部概览（当月收支统计、待办数量）
- 功能入口卡片（记账、待办）
- 未绑定 Token 时显示绑定引导

#### Step 11: 创建子页面
- `auth.vue` — Token 输入框 + 绑定按钮
- `finance.vue` — 记账列表（按日期分组，收支统计）
- `finance-add.vue` — 新增/编辑记账表单
- `todo.vue` — 待办列表（按状态分组，滑动标记完成）
- `todo-add.vue` — 新增/编辑待办表单

### 第三阶段：完善与测试（优先级 P1）

#### Step 12: 注册子页面路由
在 `src/pages.json` 的 `pages` 数组中新增子页面路由：

```json
{
  "path": "pages/life/auth",
  "style": { "navigationBarTitleText": "绑定设备", "navigationStyle": "custom", "backgroundColor": "#08090a" }
},
{
  "path": "pages/life/finance",
  "style": { "navigationBarTitleText": "记账", "navigationStyle": "custom", "backgroundColor": "#08090a" }
},
{
  "path": "pages/life/finance-add",
  "style": { "navigationBarTitleText": "记账", "navigationStyle": "custom", "backgroundColor": "#08090a" }
},
{
  "path": "pages/life/todo",
  "style": { "navigationBarTitleText": "待办", "navigationStyle": "custom", "backgroundColor": "#08090a" }
},
{
  "path": "pages/life/todo-add",
  "style": { "navigationBarTitleText": "待办", "navigationStyle": "custom", "backgroundColor": "#08090a" }
}
```

#### Step 13: 端到端测试
- 启动后端：`cd backend && node server.js`
- 启动前端：`cd .. && npm run dev:h5`
- 测试流程：绑定设备 → 新增记账 → 查看列表 → 修改 → 删除 → 新增待办 → 标记完成

---

## 3. 与现有系统的集成点

### 3.1 数据库集成

| 集成点 | 说明 |
|--------|------|
| 共用 `kanban.db` | 生活助手表与看板 `tasks` 表共存于同一 SQLite 文件 |
| 共用 `sqlite.js` 服务 | 复用 `query()`、`saveDb()`、`initDb()` 方法 |
| 启动时序 | `server.js` 中 `sqlite.initDb()` 之后调用 `lifeInitDb()` |

### 3.2 认证集成

| 集成点 | 说明 |
|--------|------|
| 复用 `config.auth.jwtSecret` | JWT 签名密钥与看板共用 |
| 独立鉴权体系 | 生活助手使用独立的 `LIFE_TOKEN` 环境变量，与看板的 `DASHBOARD_KEY` 无关 |
| 前端 Token 存储 | 看板 Token 存 localStorage，生活 JWT 也存 localStorage（不同 key） |

### 3.3 前端集成

| 集成点 | 说明 |
|--------|------|
| TabBar 第5项 | `pages.json` 已配置 `pages/life/life` 路由和 SVG 图标 |
| 样式体系 | 复用现有暗色主题（`#08090a` 背景、`#0f1011` 卡片、`#f7f8f8` 文字） |
| UI 组件库 | 复用 `uview-ui` 组件（`u-input`, `u-button`, `u-popup` 等） |
| HTTP 请求 | 复用 `uni.request`，可在现有请求拦截器中添加 JWT 注入逻辑 |

### 3.4 路由集成

| 集成点 | 说明 |
|--------|------|
| 路由挂载 | `server.js` 已导入 `lifeRouter` 并挂载到 `/api/life` |
| 限流保护 | 自动继承 `/api` 前缀的 rate limit 中间件 |
| 错误处理 | 自动继承全局 404 和 500 错误处理中间件 |

---

## 4. 注意事项和潜在坑点

### 4.1 ⚠️ sql.js 的持久化陷阱

`sql.js` 是**内存数据库**，数据不会自动写入磁盘。每次写操作（INSERT/UPDATE/DELETE）后**必须手动调用 `sqlite.saveDb()`**，否则 BFF 重启后数据丢失。

```javascript
// 正确做法：每次写操作后持久化
function createFinanceRecord(data) {
  const result = sqlite.query('INSERT INTO ...', params)
  sqlite.saveDb()  // ← 必须调用！
  return result
}
```

### 4.2 ⚠️ 并发写入冲突

`sql.js` 不支持多进程/多线程并发写入。如果 Hermes CLI 和 BFF 同时写 `kanban.db`，后保存的一方会覆盖先保存的数据。

**缓解方案**：
- BFF 写操作后立即 `saveDb()`
- 避免 BFF 与 Hermes CLI 同时操作生活助手表
- 未来可考虑迁移到 `better-sqlite3`（原生模块，支持 WAL 模式）

### 4.3 ⚠️ JWT 无刷新机制

设计上采用**长效 Token（365天）**，不实现 refresh token 机制。如果 Token 泄露，需要：
1. 修改环境变量 `LIFE_TOKEN`
2. 手动删除 `device_bindings` 表中对应的记录
3. 所有设备需要重新绑定

### 4.4 ⚠️ 单用户限制

系统设计为**单用户**（服务器预置一个 `LIFE_TOKEN`），不支持多用户。所有设备共享同一份记账和待办数据。

### 4.5 ⚠️ 前端离线不可用

需求明确"不做离线缓存"，所有操作实时走 API。手机端断网时：
- 记账/待办操作不可用
- 应给出友好的网络错误提示
- 不缓存任何数据到 localStorage（除 JWT Token 外）

### 4.6 ⚠️ 分类 ID 的跨环境一致性

预设分类通过 `INSERT OR IGNORE` 插入，ID 由 SQLite 自增分配。不同环境（开发/生产）的 `kanban.db` 中分类 ID 可能不同。前端**不应硬编码分类 ID**，必须通过 `GET /api/life/categories` 动态获取。

### 4.7 ⚠️ 金额精度

SQLite 的 `REAL` 类型是 IEEE 双精度浮点数。对于金额计算，建议：
- 存储时保留 2 位小数（前端输入时限制）
- 统计时使用 SQLite 的 `ROUND()` 函数
- 前端展示时使用 `toFixed(2)` 格式化

### 4.8 ⚠️ 现有 life.js 路由的兼容性

当前 `backend/routes/life.js` 包含技能扫描和执行历史接口。重写时有两种策略：

**策略 A（推荐）**：保留旧接口，追加新接口
- 在同一个 `life.js` 中保留 `GET /`、`GET /status`、`GET /features`、`POST /execute`、`GET /history` 等旧路由
- 追加新的记账/待办/鉴权路由
- 旧接口不加 `lifeAuth` 中间件（保持向后兼容）

**策略 B**：完全重写
- 删除所有旧接口
- 仅保留新 CRUD 接口
- 需要确认是否有前端页面依赖旧接口

> **建议采用策略 A**，确保看板其他功能不受影响。

---

## 5. 环境变量配置

在 `.env` 或 `ecosystem.config.js` 中新增：

```bash
# 生活助手 Token（手机端绑定用）
LIFE_TOKEN=your-secure-life-token-here
```

默认值（开发环境）：`life-default-token-2026`

---

## 6. 开发环境启动

```bash
# 1. 安装后端依赖
cd /home/agentuser/public/hermes-dashboard/backend
npm install

# 2. 启动后端 BFF
node server.js
# 输出：🚀 Hermes Dashboard BFF running on http://0.0.0.0:3001

# 3. 新终端，启动前端 H5
cd /home/agentuser/public/hermes-dashboard
npm run dev:h5
# 输出：http://localhost:5173

# 4. 浏览器访问 http://localhost:5173
# 5. 点击底部 Tab "生活" 进入生活助手
```

---

## 7. 测试清单

| # | 测试项 | 预期结果 |
|---|--------|---------|
| 1 | 首次访问生活 Tab | 显示绑定引导页 |
| 2 | 输入错误 LIFE_TOKEN | 提示"Token 无效" |
| 3 | 输入正确 LIFE_TOKEN | 绑定成功，跳转主页 |
| 4 | 刷新页面 | 自动登录（JWT 有效） |
| 5 | 新增一笔支出 | 列表显示，统计更新 |
| 6 | 新增一笔收入 | 列表显示，统计更新 |
| 7 | 修改记账记录 | 数据更新 |
| 8 | 删除记账记录 | 数据删除，统计更新 |
| 9 | 按日期筛选记账 | 只显示筛选范围内的记录 |
| 10 | 新增待办 | 列表显示 |
| 11 | 标记待办为完成 | 状态变更，排序变化 |
| 12 | 删除待办 | 列表移除 |
| 13 | 重启 BFF | 数据不丢失（验证 saveDb） |
| 14 | 过期 JWT | 提示重新绑定 |