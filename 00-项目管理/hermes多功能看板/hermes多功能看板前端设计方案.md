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

## 八、待后续任务完成的事项

| 事项 | 说明 | 关联任务 |
|:----|:------|:--------|
| uCharts 图表集成 | 实际接入 uCharts 组件 | M1.3 |
| SortableJS 拖拽 | 实现看板拖拽排序 | M1.3 |
| 后端接口对接 | 登录/统计/看板/Agent 接口 | M2/M3/M4 |
| 微信小程序适配 | 条件编译 + 真机调试 | M1.3 |
| LiteLLM 数据接入 | Token 用量数据真实对接 | M2 |
| 接口规范定义 | 具体接口路径/参数/返回值 | 后续任务 |
