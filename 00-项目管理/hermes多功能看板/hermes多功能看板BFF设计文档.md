# hermes多功能看板 BFF 设计文档

> **版本**：v1.1 | **日期**：2026-05-07 | **作者**：辛如音

---

## 一、前端架构概述

### 1.1 技术选型

| 领域 | 选择 | 版本 |
|:----:|:----|:----:|
| 框架 | uni-app（Vue 3） | 3.0.0 |
| UI 组件库 | uView UI 2.x | 2.0.36 |
| 图表 | uCharts | 2.5.0 |
| 状态管理 | Pinia | 2.1.7 |
| 网络请求 | uni.request 封装 | — |
| 构建工具 | Vite | 5.2.8 |
| 样式 | SCSS | 1.99.0 |

### 1.2 项目结构

```
hermes-dashboard/
├── src/
│   ├── pages/
│   │   ├── login/login.vue          # 登录页
│   │   ├── dashboard/dashboard.vue   # Token 用量统计
│   │   ├── kanban/kanban.vue         # 任务看板
│   │   └── agents/agents.vue         # Agent 运行状态
│   ├── store/
│   │   ├── user.ts                   # 用户/登录状态
│   │   ├── stats.ts                  # 统计数据
│   │   ├── kanban.ts                 # 任务看板数据
│   │   └── agents.ts                 # Agent 状态
│   ├── utils/
│   │   ├── request.ts                # uni.request 封装（BASE_URL = '/api'）
│   │   └── storage.ts                # Token 持久化
│   ├── components/                   # 公共组件
│   └── App.vue                       # 根组件
├── backend/                          # BFF 后端（本模块）
├── pages.json                        # 路由配置
├── manifest.json                     # 应用配置
└── package.json
```

### 1.3 前端启动方式

```bash
# 开发模式（H5，热更新）
cd /home/agentuser/public/hermes-dashboard
npm run dev:h5

# 构建生产版本
npm run build:h5

# 构建微信小程序
npm run build:mp-weixin

# 构建其他平台
npm run build:mp-alipay    # 支付宝小程序
npm run build:mp-baidu     # 百度小程序
npm run build:mp-toutiao   # 头条小程序
```

> **说明**：前端 `src/utils/request.ts` 已封装统一的 HTTP 请求函数，`BASE_URL = '/api'`。开发模式下 Vite 代理 `/api` 到 BFF 端口（3001），生产模式下 Nginx 反向代理 `/api` 到 BFF。

---

## 二、BFF 架构设计

### 2.1 总体架构

```
┌───────────────────┐     ┌──────────────────┐     ┌───────────────────┐
│                   │     │                  │     │                   │
│  uni-app 前端      │────▶│  BFF (Node.js)   │────▶│  LiteLLM API      │
│  (H5/小程序)       │     │  localhost:3001  │     │  localhost:4000   │
│                   │◀────│                  │◀────│                   │
└───────────────────┘     │                  │     └───────────────────┘
                           │                  │     ┌───────────────────┐
                           │                  │────▶│  PostgreSQL       │
                           │                  │     │  LiteLLM 数据库   │
                           │                  │◀────│                   │
                           │                  │     └───────────────────┘
                           │                  │     ┌───────────────────┐
                           │                  │────▶│  SQLite           │
                           │                  │     │  kanban.db        │
                           │                  │◀────│                   │
                           └──────────────────┘     └───────────────────┘
```

**BFF 层承担三种数据源的聚合**：

| 数据源 | 用途 | 协议 |
|--------|------|------|
| LiteLLM API (`:4000`) | Token 用量原始日志 | HTTP (REST) |
| PostgreSQL (`localhost:5432/litellm`) | Token 用量聚合查询 | SQL |
| SQLite (`~/.hermes/kanban.db`) | 看板任务数据 | SQL |

### 2.2 技术选型

| 组件 | 选择 | 说明 |
|:----:|:----|:------|
| 运行时 | **Node.js 22** | 已安装于服务器 |
| Web 框架 | **Express** | 轻量、生态成熟 |
| PostgreSQL 驱动 | **pg** | Node.js 原生异步驱动 |
| SQLite 驱动 | **sql.js** | 纯 JS（WASM），无需本地编译 |
| 进程管理 | **pm2** | 生产级守护 + 自动重启 |
| 开发热重载 | **nodemon** | 开发模式自动重启 |

### 2.3 目录结构

```
backend/
├── server.js          # 入口文件，Express 启动
├── config.js          # 数据库连接配置
├── routes/
│   ├── tokens.js      # Token 用量相关接口
│   ├── kanban.js      # 看板任务相关接口
│   ├── agents.js      # Agent 状态接口
│   └── auth.js        # 登录鉴权接口
├── services/
│   ├── litellmApi.js  # LiteLLM HTTP API 代理
│   ├── postgres.js    # PostgreSQL 查询服务
│   └── sqlite.js      # SQLite 查询服务
├── package.json
└── ecosystem.config.js  # pm2 配置文件
```

---

## 三、接口清单

### 3.1 认证

| 方法 | 路径 | 说明 |
|:----:|:----|:------|
| POST | `/api/auth/login` | 密钥登录验证 |
| POST | `/api/auth/verify` | Token 有效性校验 |

### 3.2 Token 用量统计

| 方法 | 路径 | 说明 |
|:----:|:----|:------|
| GET | `/api/tokens/summary` | 总览（总 Token / 总花费 / 按模型分布） |
| GET | `/api/tokens/daily` | 按日聚合趋势 |
| GET | `/api/tokens/trend` | 按粒度聚合趋势（支持 `2hour` / `daily` / `weekly`） |
| GET | `/api/tokens/by-model` | 按模型分组统计 |
| GET | `/api/tokens/models` | 有消耗记录的模型列表 |
| GET | `/api/tokens/logs` | 明细日志（分页） |

**参数说明**（统一查询参数）：

| 参数 | 类型 | 必填 | 说明 |
|:----:|:----:|:----:|:------|
| startDate | string | 否 | 开始日期 `YYYY-MM-DD`，默认 7 天前 |
| endDate | string | 否 | 结束日期 `YYYY-MM-DD`，默认今天 |
| model | string | 否 | 按模型筛选，不传则查全部 |

### 3.3 看板任务

| 方法 | 路径 | 说明 |
|:----:|:----|:------|
| GET | `/api/kanban/tasks` | 获取所有任务（支持筛选） |
| GET | `/api/kanban/tasks/:id` | 获取单个任务详情 |
| PUT | `/api/kanban/tasks/:id/status` | 更新任务状态（拖拽操作） |
| GET | `/api/kanban/stats` | 看板统计（各状态任务数） |

**筛选参数**：

| 参数 | 类型 | 说明 |
|:----:|:----:|:------|
| status | string | `backlog` / `in_progress` / `done`，不传则全量 |
| assignee | string | 按负责人英文 key 筛选 |
| priority | string | 按优先级筛选（`P0` / `P1` / `P2`，或数字 `1` / `2` / `3`） |
| project | string | 按 `workspace_path` 精确筛选（完整路径） |

> **状态值归一化**：Hermes CLI 写入状态为 `in-progress`（连字符），BFF 归一化为 `in_progress`（下划线）后返回前端；`completed` 也归一化为 `done`。统计接口 `stats` 会合并 `in_progress` + `in-progress` 和 `done` + `completed`。

### 3.4 Agent 状态

| 方法 | 路径 | 说明 |
|:----:|:----|:------|
| GET | `/api/agents` | 获取所有 Agent 运行状态 |

---

## 四、LiteLLM PostgreSQL 数据库连接方案

### 4.1 数据库连接信息

从 LiteLLM 配置文件中提取：

| 配置项 | 值 |
|:----:|:----|
| Host | `localhost` |
| Port | `5432` |
| Database | `litellm` |
| User | `agentuser` |
| Password | `litellm_local_pg` |
| 连接字符串 | `postgresql://agentuser:litellm_local_pg@localhost:5432/litellm` |

### 4.2 数据表结构

LiteLLM 使用 Prisma ORM，核心表如下：

| 表名 | 说明 | 关键字段 |
|:----:|:------|:----------|
| `LiteLLM_SpendLogs` | 原始调用日志（最详细） | `model_group`, `prompt_tokens`, `completion_tokens`, `total_tokens`, `spend`, `startTime`, `user` |
| `LiteLLM_DailyUserSpend` | 按用户/日/模型预聚合 | `date`, `user_id`, `model_group`, `prompt_tokens`, `completion_tokens`, `spend` |
| `LiteLLM_DailyTeamSpend` | 按团队/日/模型预聚合 | `date`, `team_id`, `model_group`, `prompt_tokens`, `completion_tokens`, `spend` |
| `LiteLLM_ErrorLogs` | 错误日志 | — |

### 4.3 核心 SQL 查询

#### 4.3.1 按模型分组统计（`/api/tokens/by-model`）

```sql
SELECT
  model_group,
  SUM(prompt_tokens)   AS prompt_tokens,
  SUM(completion_tokens) AS completion_tokens,
  SUM(total_tokens)    AS total_tokens,
  SUM(spend)           AS cost
FROM "LiteLLM_SpendLogs"
WHERE "startTime" >= $1::timestamp
  AND "startTime" <  $2::timestamp
GROUP BY model_group
ORDER BY total_tokens DESC;
```

#### 4.3.2 按日聚合趋势（`/api/tokens/daily`）

```sql
SELECT
  DATE(startTime)         AS day,
  SUM(prompt_tokens)      AS prompt_tokens,
  SUM(completion_tokens)  AS completion_tokens,
  SUM(total_tokens)       AS total_tokens,
  SUM(spend)              AS cost
FROM "LiteLLM_SpendLogs"
WHERE "startTime" >= $1::timestamp
  AND "startTime" <  $2::timestamp
GROUP BY DATE(startTime)
ORDER BY day;
```

#### 4.3.3 总览摘要（`/api/tokens/summary`）

```sql
-- 总览指标
SELECT
  SUM(total_tokens)      AS total_tokens,
  SUM(prompt_tokens)     AS prompt_tokens,
  SUM(completion_tokens) AS completion_tokens,
  SUM(spend)             AS total_cost
FROM "LiteLLM_SpendLogs"
WHERE startTime >= $1::timestamp
  AND startTime <  $2::timestamp;

-- 按模型分布（饼图用）
SELECT
  model_group,
  SUM(total_tokens) AS tokens
FROM "LiteLLM_SpendLogs"
WHERE "startTime" >= $1::timestamp
  AND "startTime" <  $2::timestamp
GROUP BY model_group
ORDER BY tokens DESC;
```

#### 4.3.4 模型列表（`/api/tokens/models`）

```sql
SELECT DISTINCT model_group
FROM "LiteLLM_SpendLogs"
ORDER BY model_group;
```

### 4.4 预聚合表优化

对于高频查询（如首页总览卡片），建议使用 LiteLLM 自带的预聚合表 `LiteLLM_DailyTeamSpend`，避免频繁扫描原始日志表：

```sql
-- 使用预聚合表，性能最佳
SELECT
  date,
  model_group,
  prompt_tokens,
  completion_tokens,
  spend
FROM "LiteLLM_DailyTeamSpend"
WHERE date >= $1::date
  AND date <  $2::date
ORDER BY date, model_group;
```

---

## 五、SQLite 看板数据方案

### 5.1 数据库连接

看板数据存储在本地 SQLite 文件中：

| 配置项 | 值 |
|:----:|:----|
| 文件路径 | `/home/agentuser/.hermes/kanban.db` |
| 驱动 | `sql.js`（纯 JS 方案，WASM 加载，无需本地编译） |

### 5.2 SQLite 数据库连接方案（sql.js）

**文件**：`backend/services/sqlite.js`

sql.js 通过 WASM 加载 SQLite，无需本地编译。启动时从文件加载 DB，后续 BFF 请求通过 `reloadIfChanged()` 检测文件 mtime 变化自动重载；写操作（`updateTaskStatus`）调用 `saveDb()` 持久化到磁盘。

**状态归一化函数**（`normalizeStatus`）：

```javascript
// Hermes CLI 写入 in-progress（连字符），BFF 归一化为 in_progress（下划线）
function normalizeStatus(status) {
  return status === 'in-progress' ? 'in_progress' : status
}
```

#### 5.2.1 获取任务列表（`/api/kanban/tasks`）

```sql
SELECT
  id,
  title,
  status,
  priority,
  assignee,
  workspace_path   AS project,
  workflow_template_id AS phase,
  created_at,
  started_at,
  completed_at
FROM tasks
WHERE 1=1
  AND (? = '' OR status       = ?)   -- 可选 status 筛选
  AND (? = '' OR assignee      = ?)   -- 可选 assignee 筛选
  AND (? = '' OR priority      = ?)   -- 可选 priority 筛选
  AND (? = '' OR workspace_path = ?)  -- 可选 project 筛选
ORDER BY
  CASE
    WHEN status IN ('in_progress', 'in-progress') THEN 0
    WHEN status = 'backlog'                        THEN 1
    WHEN status IN ('done', 'completed')            THEN 2
    ELSE 3
  END,
  CASE priority WHEN 'P0' THEN 0 WHEN 'P1' THEN 1 WHEN 'P2' THEN 2 END,
  created_at DESC;
```

返回格式：`{ total: number, data: Task[] }`，每条 Task 的 `status` 经过 `normalizeStatus` 处理。

#### 5.2.2 获取单个任务（`/api/kanban/tasks/:id`）

```sql
SELECT
  id, title, body, status, priority,
  assignee,
  workspace_path  AS project,
  workflow_template_id AS phase,
  created_at, started_at, completed_at,
  skills, project_name
FROM tasks WHERE id = ?;
```

#### 5.2.3 更新任务状态（`PUT /api/kanban/tasks/:id/status`）

```sql
-- done/completed：写入 completed_at
UPDATE tasks SET status = ?, completed_at = ? WHERE id = ?

-- 其他状态：清除 completed_at
UPDATE tasks SET status = ?, completed_at = NULL WHERE id = ?
```

> **注意**：BFF 写入后调用 `saveDb()` 将内存 DB 写入磁盘。

#### 5.2.4 看板统计（`/api/kanban/stats`）

```sql
SELECT status, COUNT(*) AS count
FROM tasks
GROUP BY status;
```

返回后 BFF 内存合并 `in_progress` + `in-progress` 和 `done` + `completed`，最终格式：

```json
{ "backlog": 5, "in_progress": 2, "done": 3 }
```

---

## 六、启动与部署

### 6.1 统一启动脚本

项目根目录提供统一启动脚本 `start.sh`，所有启动方式统一走此脚本：

```bash
cd /home/agentuser/public/hermes-dashboard

# 开发模式（前台运行，Ctrl+C 停止）
./start.sh

# 生产模式（pm2 后台运行）
./start.sh prod

# 停止生产服务
./start.sh stop

# 查看 pm2 服务状态
./start.sh status
```

**开发模式输出：**
- 前端 H5：`http://localhost:5173`
- BFF API：`http://localhost:3001`
- Vite 代理：`/api` → `localhost:3001`，前端无需跨域配置

**生产模式：**
1. pm2 启动 BFF（端口 3001）
2. 构建前端 H5 产物到 `dist/`
3. Nginx 托管 `dist/` 目录，`/api` 反向代理到 BFF

> ⚠️ 生产模式需先安装 pm2：`npm install -g pm2`

### 6.2 手动启动（备用）

如不使用统一脚本，可手动分步启动：

```bash
# 1. 安装后端依赖
cd /home/agentuser/public/hermes-dashboard/backend
npm install

# 2. 启动 BFF（后台运行）
cd backend && node server.js &
sleep 2
curl http://localhost:3001/health  # 验证启动成功

# 3. 启动前端开发服务器（另一个终端）
cd /home/agentuser/public/hermes-dashboard
npm run dev:h5
```

### 6.3 pm2 配置（`ecosystem.config.js`）

```javascript
module.exports = {
  apps: [{
    name: 'hermes-dashboard-bff',
    script: 'server.js',
    cwd: '/home/agentuser/public/hermes-dashboard/backend',
    instances: 1,
    exec_mode: 'fork',
    env: {
      NODE_ENV: 'production',
      PORT: 3001,
      // LiteLLM
      LITELLM_API_URL: 'http://localhost:4000',
      LITELLM_API_KEY: 'sk-litellm-masteR-kEy-2026',
      // PostgreSQL
      PG_HOST: 'localhost',
      PG_PORT: 5432,
      PG_DATABASE: 'litellm',
      PG_USER: 'agentuser',
      PG_PASSWORD: 'litellm_local_pg',
      // SQLite
      KANBAN_DB_PATH: '/home/agentuser/.hermes/kanban.db',
    },
    watch: false,
    max_memory_restart: '256M',
    error_file: './logs/error.log',
    out_file: './logs/out.log',
    merge_logs: true,
    autorestart: true,
  }]
};
```

### 6.4 Vite 代理配置（开发环境）

前端 `vite.config.ts` 已配置代理，开发模式下自动将 `/api` 请求转发到 BFF：

```typescript
// vite.config.ts 补充
export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:3001',
        changeOrigin: true,
      },
    },
  },
  // ... 现有配置
});
```

---

## 七、安全考虑

| 风险 | 防护措施 |
|:----:|:---------|
| API Key 泄露 | Key 仅配置在 `ecosystem.config.js` 环境变量中，不写死在前端代码 |
| 未授权访问 | BFF 层实现 Token 鉴权中间件，除 `/api/auth/login` 外所有接口需验证 |
| SQL 注入 | 全部使用参数化查询（PostgreSQL 的 `$1`、`$2` 占位符，SQLite 的 `?` 占位符） |
| 跨域 | 开发环境 Vite 代理处理；生产环境 Nginx 统一代理 |
| 请求限流 | Express 中间件 `express-rate-limit` 限制单 IP 请求频率 |

---

## 八、数据流示例

### 8.1 Token 统计页面加载流程

```
1. 用户打开统计页 dashboard.vue
2. → store/stats.ts → fetchSummary() + fetchDaily()
3. uni.request('/api/tokens/summary?startDate=...&endDate=...')
4. BFF /tokens/summary: 查 PostgreSQL LiteLLM_SpendLogs，返回
   { totalTokens, totalPromptTokens, totalCompletionTokens, totalCost, modelDistribution[] }
5. uni.request('/api/tokens/daily?startDate=...&endDate=...')
6. BFF /tokens/daily: 按日聚合，返回 { startDate, endDate, data: [{ date, promptTokens, completionTokens, tokens, cost }] }
7. 前端 uCharts 渲染柱状图 + 饼图
```

### 8.2 看板页面加载流程（已实现）

```
1. 用户打开任务看板页 kanban.vue
2. → store/kanban.ts → refresh() 并行调用 fetchTasks() + fetchStats()
3. fetchTasks() → GET /api/kanban/tasks（不带 project 参数，返回全量）
4. BFF 查询 SQLite kanban.db → tasks 表，经历 normalizeStatus 归一化
5. 前端本地：
   a. allTasks 保存全量任务（供 picker 选项用）
   b. project 筛选：用 shortProject() 提取 workspace_path 末段作短项目名，在前端过滤
   c. assignee/priority 筛选：BFF 查询时传递，由 SQLite WHERE 条件过滤
   d. 任务分配到 backlog / inProgress / done 三列（按 ID 升序排列）
6. fetchStats() → GET /api/kanban/stats
7. BFF 返回原始 status 计数，BFF 内存合并 in_progress+in-progress / done+completed
8. 前端渲染三列看板 + 顶部统计条
```

**拖拽更新任务状态（乐观 UI）**：

```
1. 用户拖拽任务到新列
2. store.moveTask(taskId, toStatus):
   a. 乐观更新：从旧列移除，插入新列（本地立即响应）
   b. PUT /api/kanban/tasks/{id}/status { status: toStatus }
   c. BFF UPDATE tasks + saveDb() 持久化
   d. 失败时回滚：调用 fetchTasks() 重新拉取全量
```

**负责人名称中英对照**（前端固定映射）：

| 英文 key | 中文 |
|:--------|:-----|
| `yinyue` | 银月 |
| `xingruyin` | 辛如音 |
| `ziling` | 紫灵 |
| `siyue` | 思月 |

前端 picker 显示中文，BFF 接收英文 key 筛选。

---

## 九、后续扩展

| 阶段 | 扩展内容 |
|:----:|:---------|
| 小程序版 | 增加 Cloudflare Tunnel 或 frp 提供 HTTPS 终端 |
| 实时推送 | 增加 WebSocket 端点，前端实时接收任务状态变化 |
| 缓存层 | 高频查询（如总览卡片）增加 Redis 或内存缓存，减少 PostgreSQL 压力 |
| 监控告警 | 集成 Prometheus 指标暴露端点 |
| FastAPI 迁移 | 当需要 LiteLLM Python SDK 高级能力时，可用 FastAPI 替代 BFF 层 |