# hermes多功能看板 BFF 设计文档

> **版本**：v1.6 | **日期**：2026-05-08 | **作者**：辛如音

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
| JSON 文件 (`~/.hermes/cron/jobs.json`) | Cron 定时任务状态 | 文件读 |

### 2.2 技术选型

| 组件 | 选择 | 说明 |
|:----:|:----|:------|
| 运行时 | **Node.js 22** | 已安装于服务器 |
| Web 框架 | **Express** | 轻量、生态成熟 |
| PostgreSQL 驱动 | **pg** | Node.js 原生异步驱动 |
| SQLite 驱动 | **sql.js** | 纯 JS（WASM），无需本地编译 |
| 进程管理 | **pm2** | 生产级守护 + 自动重启 |
| 开发热重载 | **nodemon** | 开发模式自动重启 |
| 健康状态持久化 | **本地 JSON 文件** | `backend/data/model-health.json`，BFF 启动自动加载 |

### 2.3 目录结构

```
backend/
├── server.js          # 入口文件，Express 启动
├── config.js          # 数据库连接配置
├── routes/
│   ├── tokens.js      # Token 用量相关接口
│   ├── kanban.js      # 看板任务相关接口（任务 CRUD + 看板统计）
│   ├── agents.js      # Agent 状态接口
│   ├── auth.js        # 登录鉴权接口
│   ├── milestone.js   # 里程碑接口（milestones + projects 三层级）
│   ├── repos.js       # Git 仓库状态接口
│   └── cronjobs.js    # Cron 定时任务状态接口
├── services/
│   ├── litellmApi.js  # LiteLLM HTTP API 代理 + 模型健康状态后台同步
│   ├── postgres.js    # PostgreSQL 查询服务
│   ├── sqlite.js      # SQLite 查询服务（任务 CRUD + 看板统计 + 待办统计）
│   ├── milestone.js   # 里程碑数据聚合服务（项目-里程碑-任务三层级）
│   └── gitRepo.js     # Git 仓库信息采集服务（每10分钟后台同步）
├── package.json
└── ecosystem.config.js  # pm2 配置文件
```

### 2.4 模型健康状态同步机制

**背景**：LiteLLM 的 cooldown 机制是内存态，不持久化到数据库。`/health` 接口直接标注了 `healthy` / `unhealthy`（unhealthy 会附带错误信息如 429），是最准的实时状态获取方式。

**架构决策**：后台定时同步（而非请求时实时获取），避免每次切换维度都等 `/health` 返回的 ~2 秒延迟。

**实现**（`backend/services/litellmApi.js`）：

```
┌─────────────────────────────────────────────────────────────────────┐
│  BFF 启动时                                                        │
│  1. 从 data/model-health.json 加载上次缓存（兜底）                  │
│  2. 立即拉取一次 LiteLLM /health + /model/info 更新缓存            │
│  3. setInterval 每 2 分钟后台同步                                   │
│                                                                    │
│  同步流程：                                                         │
│  GET /health       → 获取 healthy_endpoints / unhealthy_endpoints   │
│  GET /model/info   → 获取 model_id → model_group 映射              │
│                      ↓                                              │
│  合并构建 { model_group: 'healthy' | 'unhealthy' }                 │
│  写入内存 modelHealthStatus                                         │
│  持久化到 data/model-health.json                                    │
└─────────────────────────────────────────────────────────────────────┘
```

| 关键点 | 说明 |
|:------|:-----|
| 同步间隔 | 2 分钟（`SYNC_INTERVAL_MS = 120_000`） |
| 持久化文件 | `backend/data/model-health.json`，BFF 重启时从文件加载兜底 |
| 读取方式 | `getModelHealth()` 直接读内存，零等待 |
| 无数据兜底 | 未从 `/health` 获取到的 model_group 返回 `unknown` |
| 失败处理 | 同步失败只打 warn 日志，不影响接口正常返回 |

### 2.5 里程碑数据聚合服务（milestone.js）

**背景**：前端里程碑看板从原来的「里程碑→任务」两层结构升级为「项目→里程碑→任务」三层结构。每个项目下有多个里程碑，每个里程碑下有多个任务。

**数据模型**：

```
projects[]
├── name: string          # 项目名称（project_name）
├── total: number         # 项目总任务数
├── done: number          # 已完成任务数
├── progress: number      # 完成百分比 0-100
├── iconText: string      # 首字母大写
├── iconBg: string        # 图标背景色
└── milestones[]
    ├── name: string      # 里程碑名称（如 "MS1 — P0 核心闭环"）
    ├── total: number
    ├── done: number
    ├── progress: number
    └── tasks[]
        ├── id: string
        ├── title: string
        ├── status: string      # normalized: in_progress / done / backlog
        ├── priority: string    # P0 / P1 / P2
        ├── assignee: string    # 中文名
        └── progress: number    # 0 / 50 / 100（任务级进度）
```

**数据源**：SQLite `kanban.db`，通过 `tasks.milestone_id` 与 `milestones` 表关联

**架构流程**：

```sql
-- 核心查询：LEFT JOIN milestones 表，保留未关联任务
SELECT t.id, t.title, t.status, t.priority, t.assignee,
       t.project_name, t.milestone_id, t.milestone_sort,
       m.name AS milestone_name, m.sort_order AS milestone_order
FROM tasks t
LEFT JOIN milestones m ON t.milestone_id = m.id
WHERE t.project_name IS NOT NULL AND t.project_name != ''
ORDER BY COALESCE(m.sort_order, 999), COALESCE(t.milestone_sort, 0),
         CASE status ... END, priority, created_at DESC
```

**内存聚合逻辑**（`getMilestones()`）：

```
1. JOIN 查询获取原始行数据
2. 按 project_name 分组 → projectMap
3. 每个项目内按 milestone_id 分组 → milestoneMap
4. 无 milestone_id 的任务归入「未分组」
5. 计算每个里程碑的 total / done / progress
6. 计算项目汇总 progress
7. 按项目任务数降序排列
```

**负责人名称映射**（前端无需再传中文名）：

```javascript
const ASSIGNEE_ZH = {
  xingruyin: '辛如音',
  ziling: '紫灵',
  yinyue: '银月',
  siyue: '思月',
}
```

### 2.6 Git 仓库状态服务（gitRepo.js）

**背景**：项目有 4 个 Git 仓库（hermes-dashboard、hermes-agent、obsidian-vault、capability-platform），需要在前端展示仓库状态（分支、远程地址、最新 commit、脏文件数、同步状态等）。

**架构决策**：后台定时采集（而非请求时实时执行 git 命令），避免每次请求都 fork 子进程执行 git 命令。

**实现**：

```
┌───────────────────────────────────────────────────────────────────────┐
│ BFF 启动时                                                          │
│ 1. 从 data/repos.json 加载上次缓存（兜底）                          │
│ 2. 立即采集一次所有仓库状态                                         │
│ 3. setInterval 每 10 分钟后台采集（SYNC_INTERVAL_MS = 600000）      │
│                                                                      │
│ 采集内容（collectRepoInfo）：                                        │
│ - branch（git branch --show-current）                                │
│ - remote（优先取非 /home/ 开头的远程 URL）                           │
│ - lastCommit（git log -1: hash/message/author/timestamp）            │
│ - dirtyFiles（git status --porcelain 行数）                          │
│ - ahead/behind（git rev-list --count @{upstream}..HEAD）            │
│ - syncStatus（四态: synced/unpushed/outdated/dirty）                 │
│   → ahead>0=unpushed, behind>0=outdated, 均有=unpushed              │
│   → dirty>0 且其他正常=dirty                                         │
└───────────────────────────────────────────────────────────────────────┘
```

| 关键点 | 说明 |
|:------|:-----|
| 采集间隔 | 10 分钟 |
| 持久化文件 | `backend/data/repos.json`，BFF 重启时从文件加载兜底 |
| 读取方式 | `getRepos()` 直接读内存缓存，零等待 |
| 失败处理 | 采集失败只打 warn 日志，保留上次缓存数据 |
| 仓库配置 | 在 `config.js` 的 `repos` 数组中定义（id/name/desc/color/path） |

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
| GET | `/api/tokens/summary` | 总览（总 Token / 总花费 / 按模型分布 + 健康状态） |
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

### 3.4 里程碑（三层级）

| 方法 | 路径 | 说明 |
|:----:|:----|:------|
| GET | `/api/kanban/milestones` | 获取项目-里程碑-任务三层聚合数据 |
| GET | `/api/kanban/milestones/:id` | 获取单个里程碑详情（含任务列表） |
| GET | `/api/projects` | 获取项目列表（含进度统计） |

**里程碑接口响应格式**（`GET /api/kanban/milestones`）：

```json
{
  "total": 2,
  "data": [
    {
      "name": "hermes多功能看板",
      "total": 16,
      "done": 9,
      "progress": 56,
      "iconText": "H",
      "iconBg": "rgba(113,112,255,0.1)",
      "milestones": [
        {
          "name": "M1 — 选取前端框架",
          "total": 4,
          "done": 4,
          "progress": 100,
          "tasks": [
            {
              "id": "TSK-20260505-014",
              "title": "[M1] 选取前端框架",
              "status": "done",
              "priority": "P0",
              "assignee": "紫灵",
              "progress": 100
            }
          ]
        },
        {
          "name": "未分组",
          "total": 2,
          "done": 1,
          "progress": 50,
          "tasks": []
        }
      ]
    }
  ]
}
```

| 字段 | 类型 | 说明 |
|:----:|:----:|:------|
| `data[].name` | string | 项目名称（project_name） |
| `data[].total` | number | 项目总任务数 |
| `data[].done` | number | 已完成任务数 |
| `data[].progress` | number | 完成百分比 0-100 |
| `data[].iconText` | string | 图标首字母 |
| `data[].iconBg` | string | 图标背景色 |
| `data[].milestones[].name` | string | 里程碑名称（含 ID，如 `MS1 — P0 核心闭环`） |
| `data[].milestones[].tasks[].progress` | number | 任务级进度：0（backlog）/ 50（in_progress）/ 100（done） |
| 未分组 | — | 无 milestone_id 的任务归入 `name="未分组"` 的虚拟里程碑 |

### 3.5 Git 仓库状态

| 方法 | 路径 | 说明 |
|:----:|:----|:------|
| GET | `/api/repos` | 获取所有仓库状态（从内存缓存读取，零等待） |
| GET | `/api/repos/:id` | 获取单个仓库详情 |

**响应格式**（`GET /api/repos`）：

```json
{
  "repos": [
    {
      "id": "hermes-dashboard",
      "name": "hermes-dashboard",
      "desc": "Hermes 多功能看板前端项目（uni-app + Vue 3）",
      "color": "#7170ff",
      "path": "/home/agentuser/public/hermes-dashboard",
      "branch": "main",
      "remote": "https://github.com/...",
      "dirtyFiles": 0,
      "ahead": 0,
      "behind": 0,
      "syncStatus": "synced",
      "lastCommit": {
        "hash": "a1b2c3d",
        "message": "feat: ...",
        "author": "ziling",
        "timestamp": 1778000000
      },
      "fetchedAt": "2026-05-08T..."
    }
  ],
  "total": 4,
  "updatedAt": "2026-05-08T..."
}
```

| 字段 | 类型 | 说明 |
|:----:|:----:|:------|
| `syncStatus` | string | 四态：`synced`（同步）/ `unpushed`（未推送）/ `outdated`（落后远程）/ `dirty`（有未提交更改） |
| `dirtyFiles` | number | 未提交的更改文件数 |
| `ahead` | number | 领先远程的 commit 数 |
| `behind` | number | 落后远程的 commit 数 |
| `lastCommit` | object | 最新 commit：`{ hash, message, author, timestamp }` |
| `fetchedAt` | string | 该仓库的采集时间戳 |
| `updatedAt` | string | 全量同步时间戳 |

### 3.6 Agent 状态

| 方法 | 路径 | 说明 |
|:----:|:----|:------|
| GET | `/api/agents` | 获取所有 Agent 运行状态（含工作状态） |

**数据源**：

| 数据 | 来源 | 说明 |
|:----|:----|:-----|
| 子进程 Profile 状态 | `~/.hermes/profiles/<id>/gateway_state.json` | PID、运行状态、活跃 Agent 数 |
| 子进程默认模型 | `~/.hermes/profiles/<id>/config.yaml` | `model.default` |
| 运行时长 | `ps -p <PID> -o etimes=` | 精确秒数，避免时间戳解析歧义 |
| 主 Gateway | 固定 PID `195514` | 作为银月（`id=yinyue`）加入列表 |
| Agent 工作状态 | `~/.hermes/state.db`（主）/ `<profile>/state.db`（子） | `sessions.ended_at` + `messages.timestamp` |
| 待办任务数 | SQLite `kanban.db` | 按负责人统计 backlog 数量 |

**工作状态判断逻辑**：

```
网关未运行 → disconnected（断线，灰色）
网关运行中 → 查 state.db sessions 表：
    ended_at IS NULL（有活跃 session）
        → 查该 session 最后一条消息的 timestamp
        → 无 messages 记录 → idle（新建 session 暂无活动）
        → idleSecs = now - lastActive
        → idleSecs < 20min → working（工作中，绿色）
        → idleSecs >= 20min → idle（空闲，黄色）
    ended_at IS NOT NULL（无活跃 session）→ idle
```

**接口响应格式**：

```
GET /api/agents
```

```json
{
  "agents": [
    {
      "id": "yinyue",
      "name": "银月",
      "model": "—",
      "pid": 195514,
      "state": "running",
      "workStatus": "idle",
      "uptime": "1d 6h 8m",
      "uptimeSeconds": 108523,
      "backlogCount": 0,
      "isMain": true
    },
    {
      "id": "xingruyin",
      "name": "辛如音",
      "model": "deepseek-sensenova",
      "pid": 140909,
      "state": "running",
      "workStatus": "working",
      "uptime": "1d 8h 30m",
      "uptimeSeconds": 117044,
      "backlogCount": 8,
      "isMain": false
    }
  ]
}
```

| 字段 | 类型 | 说明 |
|:----:|:----:|:------|
| `id` | string | Agent 唯一标识（profile key） |
| `name` | string | 中文显示名 |
| `model` | string | 默认模型，`config.yaml` 中 `model.default` |
| `pid` | number | 进程 PID |
| `state` | string | Gateway 运行状态：`running` / `stopped`（仅内部使用判断断线） |
| `workStatus` | string | Agent 工作状态：`working`（工作中）/`idle`（空闲）/`disconnected`（断线） |
| `uptime` | string | Gateway 运行时长，格式 `1d 6h 8m` |
| `uptimeSeconds` | number | Gateway 运行时长（秒），精确值 |
| `backlogCount` | number | 该 Agent 待办任务数（从 kanban.db 统计） |
| `isMain` | boolean | 是否为主 Gateway（银月） |

**关键实现细节**：

- `state` 字段仅用于判断断线（`running` = Gateway 在跑，`stopped` = Gateway 已停止），前端展示用 `workStatus`
- `workStatus` 三值逻辑：网关未运行 → `disconnected`；网关运行中 + 有活跃 session + 有 messages 记录 + 最后消息 < 20 分钟 → `working`；否则 → `idle`（包括 messages 无记录的新 session）
- 活跃阈值常量：`IDLE_THRESHOLD_SECS = 1200`（20 分钟），可按需调整
- 状态数据源：主 Gateway 用 `~/.hermes/state.db`（对应主进程），子 Agent 用 `~/.hermes/profiles/<id>/state.db`（对应子进程）
- 运行时长通过 `ps -p <PID> -o etimes=` 获取秒数，格式化函数 `formatUptime(seconds)` 输出 `"1d 6h 8m"` 格式
- 主 Gateway（PID=195514）作为银月（`id=yinyue`）插入 profiles 数组首位，`isMain: true`
- 待办数来自 SQLite `tasks` 表：`SELECT assignee, COUNT(*) FROM tasks WHERE status IN ('backlog', 'in-progress', 'in_progress') GROUP BY assignee`
- profile 遍历：读取 `~/.hermes/profiles/` 目录，跳过 `shared` 子目录

### 3.7 Cron 定时任务状态

**背景**：Cron 定时任务（每日待办提醒、记忆巡检等）通过 Hermes Agent 的 cron 系统管理，数据存储在 `~/.hermes/cron/jobs.json`。BFF 负责读取该文件并转换为前端友好的格式。

| 方法 | 路径 | 说明 |
|:----:|:----|:------|
| GET | `/api/cronjobs` | 获取所有 Cron 定时任务状态 |

**数据源**：`~/.hermes/cron/jobs.json`

**响应格式**：

```json
{
  "total": 6,
  "jobs": [
    {
      "name": "每日待办提醒",
      "schedule": "0 9,19 * * *",
      "scheduleDesc": "每天 09:00、19:00",
      "state": "scheduled",
      "enabled": true,
      "status": "active",
      "statusLabel": "活跃中",
      "lastRunAt": "2026-05-08T09:00:00+08:00",
      "nextRunAt": "2026-05-08T19:00:00+08:00",
      "lastStatus": "success"
    }
  ]
}
```

| 字段 | 类型 | 说明 |
|:----:|:----:|:------|
| `name` | string | 任务名称 |
| `schedule` | string | cron 表达式 `分 时 日 月 周` |
| `scheduleDesc` | string | 中文调度描述（如 `每天 09:00、19:00`） |
| `state` | string | 调度器状态：`scheduled` / `running` / `paused` |
| `enabled` | boolean | 是否启用 |
| `status` | string | 业务状态（BFF 映射）：`active`（活跃中）/ `paused`（已暂停）/ `error`（异常） |
| `statusLabel` | string | 中文状态标签 |
| `lastRunAt` | string | 上次运行时间 |
| `nextRunAt` | string | 下次运行时间 |
| `lastStatus` | string | 上次运行结果：`success` / `error` |

**状态映射规则**：

| 原始数据 | 映射后 |
|:---------|:-------|
| `enabled=true` + `state=scheduled` | `active` / 活跃中 |
| `paused_at` 有值 | `paused` / 已暂停 |
| `last_status=error` | `error` / 异常（优先级最高） |

**调度描述解析**（`describeSchedule()` 函数，内联实现，零依赖）：

- `0 9,19 * * *` → `每天 09:00、19:00`
- `0 9 * * *` → `每天 09:00`
- `*/10 * * * *` → `每 10 分钟`
- `0 */6 * * *` → `每 6 小时`
- `0 9 * * 1-5` → `工作日 09:00`

**路径推导**：BFF 从 `config.hermes.profilesPath`（如 `/home/agentuser/.hermes/profiles/xingruyin/config.yaml`）向上回溯两级获取 Hermes 根目录，拼接 `cron/jobs.json` 路径。

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

**响应格式**（BFF 层合并模型健康状态）：

```json
{
  "totalTokens": 12345678,
  "totalPromptTokens": 5000000,
  "totalCompletionTokens": 7345678,
  "totalCost": 12.34,
  "modelDistribution": [
    { "model": "deepseek-sensenova", "tokens": 5000000, "status": "healthy" },
    { "model": "minimax-main",      "tokens": 4000000, "status": "healthy" },
    { "model": "mimo",              "tokens": 2000000, "status": "healthy" },
    { "model": "deepseek-backup",   "tokens": 1234567, "status": "healthy" }
  ]
}
```

| 字段 | 类型 | 说明 |
|:----:|:----:|:------|
| `status` | string | 模型健康状态：`healthy` / `unhealthy` / `unknown`（未从 `/health` 获取到数据的模型为 `unknown`） |
| 健康状态来源 | — | BFF 后台每 2 分钟定时同步 LiteLLM `/health` 接口，存入内存 + 本地文件持久化；前端请求时直接从内存读取，零等待 |

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
      // Hermes Agent
      HERMES_PROFILES_PATH: '/home/agentuser/.hermes/profiles',
      HERMES_MAIN_GATEWAY_PID: '195514',
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
    host: '0.0.0.0',    // 允许公网访问（Vite 默认仅监听 localhost）
    proxy: {
      '/api': {
        target: 'http://localhost:3001',
        changeOrigin: true,
        // 禁止 rewrite 路径（否则所有 /api 开头的 BFF 路由返回 404）
      },
    },
  },
  // ... 现有配置
});
```

> **说明**：Vite 默认仅监听 `127.0.0.1`，添加 `host: '0.0.0.0'` 后可通过服务器公网 IP 直接访问前端页面。`/api` 代理不 rewrite 路径，确保 BFF 路由正常工作。

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
4. BFF /tokens/summary:
   a. 查 PostgreSQL LiteLLM_SpendLogs，获取聚合指标 + 模型分布
   b. 从内存读取模型健康状态（后台每2分钟同步一次，零等待）
   c. 合并返回：{ totalTokens, ..., modelDistribution: [{ model, tokens, status }] }
5. uni.request('/api/tokens/daily?startDate=...&endDate=...')
6. BFF /tokens/daily: 按日聚合，返回 { startDate, endDate, data: [{ date, promptTokens, completionTokens, tokens, cost }] }
7. 前端 uCharts 渲染柱状图 + 饼图
8. 饼图图例每个模型名后显示状态标识：🟢正常 / 🔴异常 / ⚪未知
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

### 8.3 里程碑页面加载流程

```
1. 用户打开看板页 → 切换到里程碑 Tab
2. kanban.vue → GET /api/kanban/milestones
3. BFF milestone.js → 执行 LEFT JOIN 查询
   a. tasks LEFT JOIN milestones ON t.milestone_id = m.id
   b. 按 project_name 分组 → 按 milestone_id 分组
   c. 计算各层级 total/done/progress
   d. 无 milestone_id 任务归入「未分组」
4. 返回三层结构：projects[{name, progress, milestones[{name, progress, tasks[]}]}]
5. 前端渲染：项目卡片（宽进度条）→ 里程碑行（紧凑进度条）→ 任务明细
```

### 8.4 Git 仓库页面加载流程

```
1. 用户打开仓库信息页签 repo.vue
2. GET /api/repos
3. BFF repos.js → 直接从内存缓存 reposCache 读取（零等待）
4. 返回 4 个仓库状态数据
5. 前端渲染仓库卡片（分支名 / 同步状态 / 最后 commit / 脏文件数）
```

### 8.5 Agent 状态页面加载流程

```
1. 用户打开 Agent 状态页 agents.vue
2. → store/agents.ts → refresh() → GET /api/agents
3. BFF routes/agents.js 聚合操作：
   a. 读取 ~/.hermes/profiles/ 目录下所有子目录（跳过 shared）
   b. 每个子目录读取 gateway_state.json（获取 pid / state）
   c. 每个子目录读取 config.yaml（获取 model.default）
   d. 每个子进程 pid 执行 ps -p <PID> -o etimes= 获取运行时长（秒）
   e. 主 Gateway（固定 PID 195514）作为银月插入 profiles 数组首位
   f. 每个 Agent 读取 state.db → getAgentWorkStatus()
      - sessions 表找 ended_at IS NULL 的 session
      - messages 表查该 session 最后一条消息的 timestamp
      - 与当前时间比较，< 10min → working，≥ 10min → idle
      - 无活跃 session → idle，网关未运行 → disconnected
   g. 查询 kanban.db → getBacklogCounts() 统计各负责人待办数量
4. 返回 { agents: [...] }，前端 store 做状态映射
5. 前端 workStatus 三值展示：工作中（绿色）| 空闲（黄色）| 断线（灰色）
6. 页面无自动轮询，用户手动点击刷新按钮重新拉取
```

### 8.6 Cron 定时任务页面加载流程

```
1. 用户打开 Agent 状态页 agents.vue → 滚动到 CronJob 区域
2. uni.request GET /api/cronjobs
3. BFF routes/cronjobs.js 处理流程：
   a. 推导 Hermes 根目录：从 config.hermes.profilesPath 回溯两级
   b. 读取 ~/.hermes/cron/jobs.json（fs.readFileSync）
   c. 遍历 jobs 数组，逐条转换：
      - status 字段映射（enabled+state→active, paused_at→paused, last_status=error→error）
      - describeSchedule() 解析 cron 表达式为中文描述
   d. 返回 { total, jobs[] }
4. 前端渲染：
   a. loading 状态 → 骨架屏
   b. 数据到达 → 卡片列表（任务名 / 调度描述 / 状态标签 / 上次/下次运行时间）
   c. error 状态 → 错误提示 + 重试按钮
   d. 空数据 → 空状态提示
5. 页面无自动轮询，用户手动点击刷新按钮重新拉取
```

**前端 Agent 卡片字段映射**：

| BFF 字段 | 前端展示 | 说明 |
|:---------|:--------|:-----|
| `name` | Agent 名字 | 直接展示 |
| `model` | 默认模型 | 从 config.yaml 读取 |
| `workStatus` | 状态徽章（三色） | working=绿色/工作中，idle=黄色/空闲，disconnected=灰色/断线 |
| `uptime` | 运行时长 | 格式 `1d 8h 30m` |
| `pid` | PID | 直接展示 |
| `backlogCount` | 待办数 | 从 kanban.db 实时统计 |
| `isMain` | 主 Gateway 标识 | true 时卡片有金色边框高亮 |

**前端页面布局规范**：

- 顶部仅保留标题 + 刷新按钮（无内嵌 tab 切换，依赖底部 tabBar 导航）
- 网格布局：`grid-template-columns: repeat(2, 1fr)`，间距 10px
- 移动端防溢出：所有页面 `overflow-x: hidden; touch-action: pan-y`
- 刷新按钮样式：36px 圆形图标按钮，与任务看板页保持一致

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