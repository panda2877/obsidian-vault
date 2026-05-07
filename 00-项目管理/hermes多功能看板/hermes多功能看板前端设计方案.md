# hermes多功能看板前端设计方案

> **版本**：v1.0 | **日期**：2026-05-06 | **作者**：紫灵

---

## 一、技术选型总览

| 领域 | 选择 | 版本 | 说明 |
|:----:|:----|:----:|:----|
| 🎨 UI 组件库 | **uView UI 2.x** | `2.0.36` | 70+ 组件，有管理后台模板，SCSS 主题定制 |
| 📊 图表库 | **uCharts** | `2.6.0` | 轻量(150KB)，H5+小程序一套代码 |
| 🖱 拖拽组件 | **SortableJS** | `1.15.0` | H5 直接使用，小程序用 `@uni-helper/sortablejs` 适配版 |
| ⚡ 状态管理 | **Pinia** | `2.1.7` | Vue 3 官方推荐 |
| 🌐 网络请求 | **uni.request 封装** | 原生 | 零依赖，Promise 封装 + 拦截器 |
| ✨ CSS 方案 | **SCSS** | `1.69.5` | uni-app 原生支持，与 uView 主题配合 |
| 🛡 类型系统 | **TypeScript** | `5.3.3` | 类型安全 |

---

## 二、UI 设计风格

### 设计语言

采用 **Linear 风格** 的深色主题设计：

- **主色调**：近黑色画布 `#08090a`，面板 `#0f1011`，表面 `#191a1b`
- **品牌色**：靛蓝紫 `#5e6ad2` / `#7170ff` — 仅用于交互元素和 CTA
- **文字**：`#f7f8f8`（主要）、`#d0d6e0`（次要）、`#8a8f98`（辅助）
- **边框**：半透明白色 `rgba(255,255,255,0.08)`，而非实色边框
- **字体**：Inter（UI）+ JetBrains Mono（代码/数据）
- **层级**：通过背景亮度步进（0.02 → 0.04 → 0.05）而非阴影来表现深度

### 设计原则

1. **暗色原生**：深色不是浅色的反色，而是独立的视觉系统
2. **信息密度控制**：通过微妙的白透明度层级管理信息层级
3. **品牌色克制**：靛蓝紫只用于交互元素和品牌标识
4. **数据优先**：看板的核心是数据可读性，而非装饰

### 参考设计系统

- **Linear.app** — 暗色模式、精确排版、数据展示
- **uView Admin** — 管理后台模板、组件布局参考

---

## 三、页面设计与组件方案

### 3.1 登录页

| 项目 | 说明 |
|:----|:------|
| **布局** | 居中卡片式，logo + 密钥输入框 + 登录按钮 |
| **组件** | uView 的 `u-input` + `u-button` |
| **状态** | 默认 → 输入 → 加载 → 错误提示 |
| **交互** | 密钥错误时输入框变红 + 提示文字 |
| **密钥存储** | 环境变量（服务端比对），前端只传 key 参数 |

### 3.2 Token 用量统计

| 项目 | 说明 |
|:----|:------|
| **布局** | 顶部 4 个统计卡片 → 筛选栏 → 图表区域（柱状图 + 饼图并列） |
| **统计卡片** | 总 Token / Prompt / Completion / 费用，带环比变化 |
| **筛选栏** | 时间按钮（今天/本周/本月/自定义）+ 模型下拉框 |
| **图表** | 柱状图（趋势）+ 饼图（按模型分布），使用 uCharts |
| **组件** | uView `u-card` + uCharts 图表 + `u-dropdown` 筛选 |

### 3.3 任务看板

| 项目 | 说明 |
|:----|:------|
| **布局** | 三列 Kanban（Backlog / In Progress / Done），左导航切换 |
| **筛选** | 顶部筛选栏：项目下拉 + 负责人下拉 + 筛选按钮 |
| **任务卡片** | ID、标题、优先级 Badge、项目名，hover 上浮效果 |
| **拖拽** | 使用 SortableJS（H5）或 `@uni-helper/sortablejs`（小程序） |
| **组件** | uView `u-card` + SortableJS + 自定义 Badge 组件 |

### 3.4 Agent 运行状态

| 项目 | 说明 |
|:----|:------|
| **布局** | 2 列网格布局，每张 Agent 卡片独立展示 |
| **卡片内容** | 头像区（首字母 + 品牌色背景）、名称、当前模型、状态 Badge |
| **状态值** | Online（绿） / Offline（灰） / Error（红） |
| **统计区** | 总任务数 / 运行时长 / 并发数 三格分割 |
| **刷新** | 页面 load 时自动刷新 + 顶部手动刷新按钮 |
| **组件** | uView `u-card` + `u-tag`（状态标签）+ `u-grid`（统计区） |

---

## 四、页面路由规划

| 路径 | 页面 | 说明 |
|:----|:----|:------|
| `/pages/login/login` | 登录页 | 密钥输入，验证后跳转 |
| `/pages/dashboard/dashboard` | 统计看板 | Token 用量图表 |
| `/pages/kanban/kanban` | 任务看板 | 三列看板 + 拖拽 |
| `/pages/agents/agents` | Agent 状态 | 卡片网格展示 |
| `/pages/login/login` (未授权) | 登录页 | 未登录时重定向 |

---

## 五、项目目录结构

```
hermes-dashboard/
├── src/
│   ├── pages/
│   │   ├── login/
│   │   │   ├── login.vue
│   │   │   └── login.scss
│   │   ├── dashboard/
│   │   │   ├── dashboard.vue
│   │   │   └── dashboard.scss
│   │   ├── kanban/
│   │   │   ├── kanban.vue
│   │   │   ├── kanban.scss
│   │   │   └── components/
│   │   │       └── TaskCard.vue
│   │   └── agents/
│   │       ├── agents.vue
│   │       ├── agents.scss
│   │       └── components/
│   │           └── AgentCard.vue
│   ├── components/
│   │   ├── StatCard.vue        # 统计卡片
│   │   ├── FilterBar.vue       # 筛选栏
│   │   └── Badge.vue           # 状态 Badge
│   ├── store/
│   │   ├── index.ts            # Pinia 初始化
│   │   ├── user.ts             # 用户/登录状态
│   │   ├── stats.ts            # 统计数据
│   │   ├── kanban.ts           # 任务看板数据
│   │   └── agents.ts           # Agent 状态数据
│   ├── utils/
│   │   ├── request.ts          # uni.request 封装
│   │   └── storage.ts          # Token 持久化
│   ├── static/
│   │   └── images/
│   ├── uni.scss                # 全局 SCSS 变量
│   └── App.vue                 # 根组件
├── pages.json                  # 路由配置
├── manifest.json               # 应用配置
├── uni_modules/                # uni-app 插件
└── package.json
```

---

## 六、关键配置

### uView UI 配置

```typescript
// main.ts
import uview from 'uview-ui'
import { createPinia } from 'pinia'

const app = createApp(App)
app.use(uview)
app.use(createPinia())
app.mount('#app')
```

### 主题定制（uni.scss）

```scss
// uView 主色调覆盖
$u-primary: #5e6ad2;
$u-primary-dark: #4a54b8;
$u-primary-light: #828fff;

// 背景色
$u-bg-color: #08090a;
$u-bg-color-page: #0f1011;

// 文字
$u-main-color: #f7f8f8;
$u-content-color: #d0d6e0;
$u-tips-color: #8a8f98;
$u-light-color: #62666d;

// 边框
$u-border-color: rgba(255,255,255,0.08);

// 圆角
$u-border-radius: 6px;
$u-border-radius-large: 8px;
```

### 请求封装

```typescript
// utils/request.ts
import { useUserStore } from '@/store/user'

const BASE_URL = '/api'

export function request<T>(options: {
  url: string
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  data?: any
}): Promise<T> {
  return new Promise((resolve, reject) => {
    const userStore = useUserStore()
    uni.request({
      url: BASE_URL + options.url,
      method: options.method || 'GET',
      data: options.data,
      header: {
        'Authorization': `Bearer ${userStore.token}`,
        'Content-Type': 'application/json',
      },
      success: (res) => {
        if (res.statusCode === 401) {
          userStore.logout()
          uni.reLaunch({ url: '/pages/login/login' })
          reject(res.data)
        } else {
          resolve(res.data as T)
        }
      },
      fail: reject,
    })
  })
}
```

---

## 七、UI 原型预览

同目录下的 `hermes多功能看板前端设计方案.html` 文件包含了完整的可交互 UI 原型。

**原型内容**：
- 🔐 登录页 — 密钥输入验证
- 📊 统计看板 — 4 个统计卡片 + 柱状图 + 饼图 + 时间筛选
- 🎯 任务看板 — 三列 Kanban + 筛选栏 + 任务卡片
- 🤖 Agent 状态 — 4 个 Agent 卡片网格

**原型功能**：
- 密钥登录演示（密钥：`hermes-secret-key`）
- 页面切换导航
- 时间筛选切换
- 手动刷新交互
- Tweaks 预览面板

**打开方式**：直接浏览器打开 HTML 文件即可

---

## 八、二期新增页面与页签规划

> **版本**：v2.0（二期） | **日期**：2026-05-07 | **作者**：紫灵

### 8.1 总体变更一览

| 变更 | 位置 | 说明 |
|:----|:----|:------|
| 🆕 Git 仓库信息 | 底部栏新增页签 | 与统计/任务/Agent 平级，排在 Agent 右侧 |
| 🆕 里程碑看板 | 任务页签下二级切换 | 在"任务看板"标题与刷新按钮之间加切换 bar |
| 🆕 CronJob 状态 | Agent 页签下二级切换 | Agent 标题改为"Agent"，在标题与刷新按钮间加切换 bar |
| ✏️ Agent 标题变更 | Agent 页面 | 原"Agent 状态" → "Agent" |

### 8.2 底部栏页签扩展

```
底部 TabBar（从左到右）：
┌──────┬──────┬──────┬──────┐
│ 统计  │ 任务  │ Agent │ 仓库  │ ← 新增
└──────┴──────┴──────┴──────┘
```

- **路由**：`/pages/repo/repo` → Git 仓库信息页
- **图标**：复用现有 SVG 图标风格，使用 git-branch / code 相关图标
- **pages.json** 新增 tabBar 配置项

### 8.3 任务页签下 — 二级切换栏

在任务看板（kanban.vue）顶部，标题「任务看板」与刷新按钮之间插入切换 bar：

```
┌──────────────────────────────────────────────┐
│  任务看板          [任务看板 | 里程碑看板]   ↻  │
└──────────────────────────────────────────────┘
```

- **状态 A「任务看板」**：当前的三列 Kanban 内容不变
- **状态 B「里程碑看板」**：展示里程碑进度视图
- **切换 bar 样式**：与现有 `nav-tabs` 风格一致（`#0f1011` 底、`#191a1b` 激活态）

#### 里程碑看板内容（示意）

里程碑看板展示 Hermes 项目的里程碑进度，以表格/列表形式呈现：

- 每行一个里程碑（如 M1/M2/M3/M4）
- 显示：里程碑名称、总任务数、完成数、进度百分比、进度条
- 展开可查看该里程碑下的子任务明细

### 8.4 Agent 页签下 — 二级切换栏

在 Agent 页（agents.vue）顶部，标题改为「Agent」，在标题与刷新按钮之间插入切换 bar：

```
┌──────────────────────────────────────────────┐
│  Agent               [状态 | CronJob]       ↻  │
└──────────────────────────────────────────────┘
```

- **标题变更**：原 `Agent 状态` → `Agent`
- **状态 A「状态」**：当前的 Agent 卡片网格内容
- **状态 B「CronJob」**：展示定时任务 / cronjob 状态视图

#### CronJob 状态内容（示意）

CronJob 页面展示 Hermes 中注册的定时任务：

- 每行一个 cronjob
- 显示：名称、调度表达式（cron）、上次运行时间、下次运行时间、状态（正常/异常）、最近一次运行结果
- 支持按状态筛选、手动触发

### 8.5 路由规划（二期新增）

| 路径 | 页面 | 说明 |
|:----|:----|:------|
| `/pages/repo/repo` | Git 仓库信息 | 底部栏新增页签，展示仓库状态 |
| `/pages/kanban/kanban` | 任务看板（扩展） | 增加里程碑子视图切换 |
| `/pages/agents/agents` | Agent（扩展） | 增加 CronJob 子视图切换 |

### 8.6 样式优化建议

基于一期已实现的 uView + uni-app 暗色主题，二期提出以下优化点：

#### 8.6.1 页面间切换动画

当前页面切换（tabBar 切换）缺少过渡效果，建议添加：

```scss
// App.vue 或全局样式
.page-enter-active, .page-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.page-enter-from { opacity: 0; transform: translateY(8px); }
.page-leave-to { opacity: 0; transform: translateY(-4px); }
```

#### 8.6.2 统计看板布局优化

当前 dashboard 统计卡片为 2 列网格（`grid-template-columns: repeat(2, 1fr)`），在大屏上显得稀疏。建议：

- **PC/H5 大屏**：使用 `repeat(4, 1fr)` 让四个卡片并排
- **移动端**：保持 `repeat(2, 1fr)` 或切换为 `repeat(1, 1fr)` 纵向排列
- 利用 `@media` 查询做响应式适配

#### 8.6.3 统一刷新按钮交互

kanban.vue 和 agents.vue 都有刷新按钮，但 dashboard.vue 没有。建议统一：

- 所有页面标题栏右侧统一添加刷新按钮
- 刷新时 icon 旋转动画（一期 kanban/agents 已有，统一即可）

#### 8.6.4 卡片悬停与微交互

- 统计卡片（stat-card）添加 hover 微上浮 + 边框亮度变化（类似 task-card 的效果）
- Agent 卡片添加 hover 效果：微上浮 + 阴影增强
- 切换 bar 的 tab 切换添加平滑过渡动画

#### 8.6.5 空状态统一

- 统一空状态展示样式（目前 kanban 列空有「暂无任务」，agents 有「暂无运行中的 Agent」）
- 建议抽取为 `<EmptyState>` 公共组件，支持自定义 icon + 文案 + 操作按钮

#### 8.6.6 加载骨架屏

- 统计卡片、任务卡片、Agent 卡片在首次加载时显示骨架屏（skeleton）
- 使用 uView 的 `u-skeleton` 组件或自定义 CSS 骨架屏
- 避免白屏或纯文字"加载中..."的突兀感

#### 8.6.7 品牌色与交互色统一

一期中存在少量颜色不一致：

- 品牌色 `#5e6ad2` 和 `#7170ff` 在不同地方混用
- 建议统一为 `#5e6ad2`（按钮背景）/ `#7170ff`（高亮文本/边框）
- Badge 组件的颜色与主题色对齐

### 8.7 目录结构变更（二期）

```
hermes-dashboard/
├── src/
│   ├── pages/
│   │   ├── repo/                    ← 新增
│   │   │   ├── repo.vue
│   │   │   └── repo.scss
│   │   ├── kanban/
│   │   │   ├── kanban.vue
│   │   │   ├── components/
│   │   │   │   ├── KanbanBoard.vue   ← 拆分：看板视图
│   │   │   │   └── MilestoneBoard.vue ← 新增：里程碑视图
│   │   │   └── kanban.scss
│   │   └── agents/
│   │       ├── agents.vue
│   │       ├── components/
│   │       │   ├── AgentStatus.vue    ← 拆分：状态视图
│   │       │   └── CronJobList.vue    ← 新增：CronJob 视图
│   │       └── agents.scss
│   ├── store/
│   │   ├── repo.ts                   ← 新增：Git 仓库 Store
│   │   ├── milestone.ts              ← 新增：里程碑 Store
│   │   └── cronjob.ts                ← 新增：CronJob Store
│   └── components/
│       └── EmptyState.vue             ← 新增：空状态组件
```

---

## 九、UI 原型预览（二期）

同目录下的 `hermes多功能看板前端设计方案.html` 文件已更新，包含二期新增页面原型。

**新增原型内容**：
- 🆕 底部栏增加「仓库」页签（与统计/任务/Agent 平级）
- 🆕 任务页签下「任务看板 | 里程碑看板」切换 bar
- 🆕 Agent 页签下「状态 | CronJob」切换 bar
- 🆕 Git 仓库信息页面内容
- 🆕 里程碑进度一览页面内容
- 🆕 CronJob 状态页面内容

---

## 十、二期待实现事项

| 事项 | 说明 | 优先级 | 关联任务 |
|:----|:------|:-----:|:--------|
| 底部栏新增仓库页签 | pages.json 路由 + tabBar 配置 + repo.vue 页面 | P0 | M4.1 |
| 任务页签二级切换栏 | kanban.vue 顶部切换 bar + 里程碑视图 | P0 | M4.1 |
| Agent 页签二级切换栏 | agents.vue 顶部切换 bar + CronJob 视图 | P0 | M4.1 |
| Git 仓库信息页面开发 | 仓库列表、分支信息、提交记录展示 | P0 | M4.2 |
| Skill 信息页签 | Agent 页签下新增 skill 信息子视图 | P1 | M4.3 |
| CronJob 状态页面开发 | cronjob 列表、调度表达式、运行记录 | P0 | M4.4 |
| 里程碑进度数据对接 | BFF 接口开发，里程碑数据聚合 | P0 | M3.5 |
| 样式优化落地 | 骨架屏、统一刷新、响应式布局、空状态组件 | P1 | M4.1 |
| 页面切换动画 | 全局过渡动画配置 | P2 | M4.1 |
