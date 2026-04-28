# Hermes AI Workspace 调研报告

**调研时间：** 2026-04-25  
**调研范围：** "Hermes AI Workspace" 产品调研

---

## 一、核心发现（先说结论）

**"Hermes AI Workspace" 不是 Nous Research 的官方产品。**

经全面搜索，**不存在**名为 "Hermes AI Workspace" 的独立产品包或品牌。与之最相关的有两个事物：

| 名称 | 性质 | 链接 |
|------|------|------|
| **Hermes Agent** | Nous Research 开发的官方 AI Agent 产品（即当前已部署的 `hermes-cli`） | https://github.com/NousResearch/hermes-agent |
| **Pan by Euraika** | 第三方社区项目，定位为"Hermes Agent 的 Web Workspace UI" | https://github.com/Euraika-Labs/pan-ui |

如果"Hermes AI Workspace"指的是 Pan，则可以安装；如果指的是某个独立的官方产品，则不存在。

---

## 二、"Hermes Agent" 官方产品详情

### 2.1 产品定位

Hermes Agent 是 **Nous Research** 开发的自主型 AI Agent，核心特点是内置学习闭环：

- 从经验中创建 Skills并在使用中自我改进
- 跨会话记忆和用户建模
- 支持 15+ 消息平台（Telegram、Discord、WhatsApp、Signal 等）
- 6 种终端后端：本地、Docker、SSH、Daytona、Singularity、Modal
- 支持 OpenRouter、NVIDIA NIM、OpenAI、Anthropic、Kimi、MiniMax 等多模型

### 2.2 官方资源

| 项目 | 地址 |
|------|------|
| 官网 | https://hermes-agent.nousresearch.com |
| 文档 | https://hermes-agent.nousresearch.com/docs/ |
| GitHub | https://github.com/NousResearch/hermes-agent (⭐ 11.5k) |
| Discord | https://discord.gg/NousResearch |

### 2.3 主要功能

- **CLI 交互**：`hermes` 命令启动 TUI 界面，支持流式工具输出、多行编辑、斜杠命令自动补全
- **消息网关**：`hermes gateway` 支持 Telegram/Discord/Slack/WhatsApp/Signal/Email 等平台
- **内置 Dashboard**：`hermes dashboard`（Web UI，端口 9119）可管理配置、API Key 和会话
- **Skills 系统**：可从 agentskills.io 安装社区 Skills，Agent 可自主创建和复用
- **记忆系统**：FTS5 全文搜索 + LLM 摘要跨会话记忆
- **MCP 集成**：连接任何 MCP 服务器
- **Cron 调度**：自然语言配置定时任务
- **ACP 协议**：支持 VS Code、Zed、JetBrains 等 IDE 集成

### 2.4 安装方式

```bash
# 官方安装脚本
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash

# Android/Termux
# Linux/macOS/WSL2 均支持
```

### 2.5 授权方式

**MIT 许可证**（开源免费）

---

## 三、Pan by Euraika（最可能的"Workspace"候选）

这是第三方社区项目，npm 包名 `@euraika-labs/pan-ui`，是唯一一个以"workspace"概念包装 Hermes Agent 的产品。

### 3.1 基本信息

| 项目 | 内容 |
|------|------|
| 当前版本 | 0.7.2（2026-04-10 更新）|
| GitHub | https://github.com/Euraika-Labs/pan-ui (⭐ 52) |
| npm | https://www.npmjs.com/package/@euraika-labs/pan-ui |
| 许可证 | MIT |
| 技术栈 | Next.js + TypeScript + React + TanStack Query + Radix UI |

### 3.2 核心功能

- **Chat** — SSE 流式聊天，连接 Hermes 运行时，带工具时间线、审批卡片
- **Skills 管理** — 从 skills.sh 搜索/安装，读取 `~/.hermes/skills/`
- **MCP Hub** — 浏览/安装/配置 MCP 服务端
- **Plugins 工作区** — 管理插件
- **Memory** — 读写 `USER.md` / `MEMORY.md`（全局和 Profile 级别）
- **Profiles** — 管理 `~/.hermes/profiles/<name>/` 多配置
- **运行时诊断** — 会话 API、认证、工具状态

### 3.3 安装方式（一键）

```bash
# 前置条件：Node.js 18+
npx @euraika-labs/pan-ui

# 首次运行会自动启动 Hermes Gateway（若未运行）
# 之后访问 http://localhost:3199
```

**后台运行：**
```bash
npx @euraika-labs/pan-ui start --daemon
npx pan-ui status
npx pan-ui logs
npx pan-ui stop
```

**系统服务（Linux）：**
```bash
npx @euraika-labs/pan-ui service install  # 创建 systemd user service
```

### 3.4 与 Hermes Agent 的关系

架构图：
```
Browser ──SSE/fetch──▶ Pan (Next.js, :3199)
                           │
                           ▼
                     Hermes Gateway (:8642)
                     Hermes Filesystem (~/.hermes/)
                     Hermes Agent sessions
```

- Pan 会**自动检测并启动** Hermes Gateway（若未运行）
- 使用 Hermes 的 OpenAI 兼容 SSE 端点进行流式对话
- Skills/Memory/Profiles 均读写同一份 `~/.hermes/` 文件

### 3.5 注意事项

- ⚠️ Pan 使用 **Euraika-Labs 维护的 Hermes Fork**（非官方 NousResearch/hermes-agent）
- ⚠️ 社区项目，非 Nous Research 官方产品
- 有自己的 `/workspace_username` / `/workspace_password` 认证体系（默认 `admin`/`changeme`）
- 通过 `hermes.version.json` 固定 Hermes 版本

---

## 四、当前环境分析

### 4.1 现有环境

```
操作系统：    Linux x86_64 (6.8.0)
Python：      3.11.15 (virtualenv: /home/agentuser/.hermes/hermes-agent/venv)
Node.js：    v22.22.2 ✅
npm：        10.9.7 ✅
已安装：      Hermes Agent（ NousResearch/hermes-agent，11.5k ⭐）
配置目录：    ~/.hermes/（完整配置、skills、memory、sessions）
Gateway：     已运行（端口 8642）
Dashboard：   `hermes dashboard` 已有（端口 9119）
```

### 4.2 Hermes Agent 内置 Dashboard vs Pan

| 对比项 | `hermes dashboard`（官方内置） | Pan（第三方） |
|--------|------|------|
| 管理配置 | ✅ | ✅ |
| 管理 API Keys | ✅ | ✅ |
| 管理会话 | ✅ | ✅ |
| Chat 界面 | ✅ | ✅ 更美观 |
| Skills 管理 | ❌ | ✅ |
| MCP Hub | ❌ | ✅ |
| 授权登录 | ❌（本地访问） | ✅（用户名密码）|
| 多 Profile UI | 有限 | ✅ |
| 许可证 | MIT | MIT |

---

## 五、结论与建议

### 5.1 "Hermes AI Workspace"是否存在？

**不存在以此命名的独立产品。** 可能的情况：

1. **指 Pan by Euraika** — 第三方 Web Workspace，npm 可直接安装，**推荐尝试**
2. **指 Hermes Agent 本身** — 已安装，无需额外安装
3. **指 hermes-ai (PyPI)** — 另一个无关的 LlamaIndex 封装库，与 Nous Research 无关

### 5.2 能否安装 Pan？

**可以**，环境完全满足：

- ✅ Linux x86_64
- ✅ Node.js 18+（当前 v22）
- ✅ Hermes Agent 已运行
- ✅ Python 3.11 已有

### 5.3 与现有 hermes-cli 配合？

**可以**，但不建议同时使用两个 Web UI：

- Pan 使用 `:8642` Gateway 端口，`hermes dashboard` 使用 `:9119`
- 两者都读 `~/.hermes/` 配置，**数据完全一致**
- 同时运行不会冲突，但功能重复

### 5.4 建议

| 场景 | 建议 |
|------|------|
| 只需要管理 Agent | 继续使用已有的 `hermes dashboard`（:9119），无需额外安装 |
| 需要 Skills/MCP 可视化管理 | 安装 Pan（`npx @euraika-labs/pan-ui`），同时运行两者 |
| 需要更美观的多会话 UI | Pan 更适合 |
| 生产环境 | 谨慎——Pan 是第三方项目，非官方维护 |

---

## 附录：PyPI 上另一个 "hermes-ai"

```
名称： hermes-ai
版本： 0.3.20
说明： "Hermes is a lightweight, powerful abstraction layer over LlamaIndex 
       that simplifies building production-ready AI agents"
作者： None（无作者信息）
```

⚠️ **此包与 Nous Research 或 Hermes Agent 完全无关**，是一个独立的 LlamaIndex 封装库。

---

*调研完成。以上信息基于 2026-04-25 的公开数据。*
