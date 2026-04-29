# Hermes Agent 与 OpenClaw 技术对比

> **版本**：v1.0
> **日期**：2026-04-29
> **作者**：如音（幸如音）
> **分类**：技术选型 / 竞品分析

---

## 一、背景说明

**OpenClaw** 是 Nous Research（SparkLab）开发的开源 AI Agent 框架，代号 Claw3D，使用 TypeScript 开发，曾拥有完整的消息平台集成（飞书、微信等）和 SOUL persona 系统。

**Hermes Agent** 是 Nous Research 推出的下一代 Python 版 Agent 框架，可视为 OpenClaw 的正式继承者。官方提供了从 OpenClaw 完整迁移到 Hermes 的工具链（`hermes claw migrate`）。

两者同源，功能高度重叠，本文做系统性对比，供技术选型参考。

---

## 二、核心架构对比

| 维度 | Hermes Agent | OpenClaw（Claw3D） |
|------|-------------|-------------------|
| **开发语言** | Python 3 | TypeScript |
| **代码规模** | ~3000 pytest 测试 | 规模较小 |
| **插件生态** | Python 包生态（pip） | TypeScript npm 生态 |
| **入口形式** | CLI + Gateway 双入口 | 单一 CLI 入口 |
| **消息格式** | OpenAI Chat Completions | OpenAI Chat Completions |

---

## 三、功能维度对比

### 3.1 模型与 Provider 支持

| 维度 | Hermes Agent | OpenClaw |
|------|-------------|---------|
| Provider 数量 | 20+（OpenRouter、Anthropic、OpenAI、DeepSeek、Google Gemini、MiniMax 等） | 较少，集中在主流 Provider |
| 凭证池 | 支持多 API Key 自动轮换 | 不支持 |
| 模型切换 | `hermes model` 交互式切换，热切换 | 需要修改配置 |
| 本地模型 | 支持（llama.cpp、vLLM） | 有限支持 |

**结论**：Hermes 在模型灵活性上显著领先，凭证池机制对团队使用更友好。

---

### 3.2 工具系统（Tools）

| 维度 | Hermes Agent | OpenClaw |
|------|-------------|---------|
| 内置工具集 | 20+（terminal、file、web、browser、code_execution、vision、mcp 等） | 基础工具集 |
| 工具管理 | `hermes tools enable/disable` 交互式 | 配置文件管理 |
| MCP 集成 | 原生支持（1050+ 行 MCP client） | 插件扩展 |
| 审批机制 | 危险命令二次确认（approval） | 基础 |
| Webhook | 原生支持（`hermes webhook subscribe`） | 不支持 |

**结论**：Hermes 工具链更完整，特别是 MCP 支持和 Webhook 是 OpenClaw 缺少的企业级能力。

---

### 3.3 Skills 自学习系统

| 维度 | Hermes Agent | OpenClaw |
|------|-------------|---------|
| Skill 机制 | 保存为 Markdown 文件，可跨 session 持久化 | SOUL.md persona 机制 |
| Skill 市场 | `hermes skills browse` 在线市场 | 有限 |
| 自改进 | 解决复杂问题后可存为 skill，后续自动加载 | 不支持 |
| Skill 分类 | 14+ 分类（devops、mlops、data-science、social-media 等） | 较少 |

**结论**：Hermes 的 Skill 机制将"经验积累"系统化，OpenClaw 的 SOUL.md 更偏向角色扮演。

---

### 3.4 记忆与持久化

| 维度 | Hermes Agent | OpenClaw |
|------|-------------|---------|
| 跨 Session 记忆 | 持久化记忆（memory tool） | MEMORY.md / USER.md |
| 记忆后端 | 内置 / Honcho / Mem0 可选 | Honcho |
| 上下文压缩 | 自动（token 阈值触发） | 手动 |
| Session 存储 | SQLite FTS5 全文搜索 | 文件系统 |
| Session 导出 | JSONL 导出 | 有限 |

**结论**：Hermes 的记忆系统更成熟，压缩机制避免 context 溢出，搜索能力更强。

---

### 3.5 消息平台集成（Gateway）

| 维度 | Hermes Agent | OpenClaw |
|------|-------------|---------|
| 平台数量 | 15+（Telegram、Discord、Slack、WhatsApp、Signal、Matrix、Email、飞书、微信等） | 飞书、微信等少量平台 |
| 连接模式 | WebSocket 长连接 + Webhook 双模式 | Webhook |
| 消息处理 | 串行（避免并发问题）+ 去重 | 基础去重 |
| 群组支持 | @mention 门控、允入名单 | 有限 |
| Home 频道 | 支持设置默认首页频道 | 不支持 |

**结论**：Hermes Gateway 覆盖面更广，协议实现更完整。

---

### 3.6 多 Agent 与调度

| 维度 | Hermes Agent | OpenClaw |
|------|-------------|---------|
| 子 Agent 委托 | `delegate_task` 原生支持 | Honcho 集成 |
| 多 Agent 协作 | Worktree 模式（隔离 git） | TypeScript 插件 |
| Cron 调度 | `hermes cron` 原生支持 | 外部 cron |
| Profiles | 多独立实例（配置/记忆/技能隔离） | 不支持 |

**结论**：Hermes 在多实例隔离和计划任务上有原生优势，OpenClaw 依赖外部编排。

---

### 3.7 开发与可扩展性

| 维度 | Hermes Agent | OpenClaw |
|------|-------------|---------|
| 开发文档 | 完整（官网 + 开发者指南） | 较少 |
| 测试覆盖 | ~3000 pytest 测试 | 有限 |
| 插件系统 | Python 标准插件接口 | TypeScript 插件 |
| 贡献活跃度 | 活跃（tekNium 主导，大量社区 PR） | 已放缓 |
| 迁移路径 | `hermes claw migrate` 官方迁移 | — |

---

## 四、使用难易程度对比

### 4.1 安装配置

| 维度 | Hermes Agent | OpenClaw |
|------|-------------|---------|
| 一键安装 | `curl -fsSL .../install.sh \| bash` | 手动 clone + npm install |
| 首次配置 | `hermes setup` 交互式向导（含 OpenClaw 迁移检测） | 手动编辑配置文件 |
| Docker 支持 | 有 | 有 |
| 最小依赖 | Python 3.10+ | Node.js 18+ |

**结论**：Hermes 安装更简洁，配置向导更友好。

### 4.2 日常使用

| 维度 | Hermes Agent | OpenClaw |
|------|-------------|---------|
| 交互模式 | CLI / TUI / 消息平台 | 纯 CLI |
| 命令行界面 | Slash commands（`/new`, `/skill`, `/model` 等） | 基础命令 |
| 学习曲线 | 中等（功能多，需要熟悉 skills/profiles） | 较低（功能集中） |
| 调试手段 | `hermes doctor` 自检，`hermes logs` | 手动日志 |

### 4.3 迁移成本（OpenClaw 用户）

- **官方迁移工具**：`hermes claw migrate` 支持完整迁移（SOUL.md、MEMORY、USER、Skills、命令白名单、消息配置、API Keys、TTS 资产）
- 迁移过程有 dry-run 预览，可分阶段执行
- **结论**：从 OpenClaw 迁出成本低，官方保证平滑过渡

---

## 五、优势与劣势总结

### Hermes Agent

**优势**：
- ✅ Python 生态，扩展容易（pip install 即可引入新依赖）
- ✅ 20+ LLM Provider 支持，凭证池机制适合团队
- ✅ Skills 自学习系统，让 Agent 越用越强
- ✅ 15+ 消息平台原生集成，Gateway 成熟
- ✅ Profiles 多实例隔离，适合多角色场景
- ✅ MCP 原生支持，企业集成能力强
- ✅ Cron + Webhook 事件驱动能力完整
- ✅ 活跃开发，频繁迭代（v0.2 → v0.9+ 多个版本）
- ✅ ~3000 测试用例，稳定性和可维护性高

**劣势**：
- ❌ Python GIL 限制，多线程并发有瓶颈（但异步 IO 已优化）
- ❌ 功能多，上手复杂度高于 OpenClaw
- ❌ TUI 模式需要额外依赖（ink + React）

---

### OpenClaw（Claw3D）

**优势**：
- ✅ TypeScript 原生类型，IDE 支持好
- ✅ 体积小，资源占用低
- ✅ 对已习惯 TypeScript 的团队友好
- ✅ SOUL.md persona 简洁直观

**劣势**：
- ❌ 开发已放缓，主要维护者转向 Hermes
- ❌ Provider 支持少，不支持凭证池
- ❌ 无 Skills 自学习系统，经验无法积累
- ❌ 无原生 Cron/Webhook，依赖外部
- ❌ 消息平台集成较少
- ❌ Profiles 多实例不支持
- ❌ 无官方迁移到其他框架的路径（Hermes 有迁出但 OpenClaw 没有）

---

## 六、选型建议

| 场景 | 推荐 | 理由 |
|------|------|------|
| **新项目选型** | Hermes Agent | 功能完整，活跃开发，生态完善 |
| **TypeScript 技术栈** | OpenClaw（若继续维护） | 语言一致性优先 |
| **团队协作（多用户）** | Hermes Agent | 凭证池 + Profiles 隔离 |
| **AI 自改进需求** | Hermes Agent | Skills 持久化机制 |
| **企业集成（MCP/Webhook）** | Hermes Agent | 原生支持 |
| **资源受限环境** | OpenClaw | 体积更小 |
| **已使用 OpenClaw** | 迁移到 Hermes | 官方提供完整迁移工具 |

---

## 七、关键参考链接

- Hermes Agent 官网：https://hermes-agent.nousresearch.com
- Hermes Agent GitHub：https://github.com/NousResearch/hermes-agent
- OpenClaw（已归档）：历史版本迁移入口
- 官方迁移指南：`hermes claw migrate --help`

---

*本文档由如音撰写，完成时间 2026-04-29*
