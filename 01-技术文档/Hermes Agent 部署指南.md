# Hermes Agent 部署指南

## 概述

Hermes Agent 是 Nous Research 开源的多平台 AI Agent 框架，支持在终端、即时通讯平台（飞书、微信、Discord、Telegram 等）运行，可连接 20+ LLM 提供商，具备跨会话持久记忆、Skills 自学习、多 Agent 协作等能力。

**官方文档**：https://hermes-agent.nousresearch.com/docs/
**GitHub**：https://github.com/NousResearch/hermes-agent

---

## 1. 安装

### 快速安装

```bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
```

### 验证安装

```bash
hermes --version      # 查看版本
hermes doctor         # 检查依赖和配置
```

### 升级

```bash
hermes update
```

---

## 2. API 接入（模型供应商）

### 支持的提供商

| 提供商 | 认证方式 | 环境变量 |
|--------|----------|----------|
| OpenRouter | API Key | `OPENROUTER_API_KEY` |
| Anthropic | API Key | `ANTHROPIC_API_KEY` |
| DeepSeek | API Key | `DEEPSEEK_API_KEY` |
| xAI / Grok | API Key | `XAI_API_KEY` |
| Google Gemini | API Key | `GOOGLE_API_KEY` |
| MiniMax | API Key | `MINIMAX_API_KEY` |
| Hugging Face | Token | `HF_TOKEN` |
| 自定义端点 | Config | `model.base_url` + `model.api_key` |

完整列表参考：[Providers 文档](https://hermes-agent.nousresearch.com/docs/integrations/providers)

### 配置方式

**方式一：交互式向导**
```bash
hermes setup          # 完整向导（选择 model|terminal|gateway|tools|agent）
hermes model          # 仅更换模型/提供商
```

**方式二：命令行直接设置**
```bash
hermes config set model.provider openrouter
hermes config set model.default anthropic/claude-sonnet-4-7
hermes config set model.api_key sk-xxx
```

**方式三：手动编辑配置**
```bash
hermes config edit   # 打开 config.yaml 编辑器
```

配置文件位置：`~/.hermes/config.yaml`
密钥文件位置：`~/.hermes/.env`（API Key 等敏感信息放这里）

### 自定义端点示例（MiniMax）

```yaml
model:
  provider: custom
  base_url: https://api.minimaxi.com/anthropic
  api_key: your_minimax_api_key
  default: MiniMax-M2.7
```

### 凭证池（多 Key 轮换）

```bash
hermes auth add                    # 交互式添加凭证
hermes auth list                  # 查看当前凭证池
hermes auth list openrouter        # 查看特定提供商凭证
hermes auth remove openrouter 1   # 移除第 2 个凭证
```

---

## 3. 渠道接入（Messaging Platforms）

### 支持的渠道

| 平台 | 说明 |
|------|------|
| **飞书 (Feishu)** | 需提供 App ID + App Secret |
| **微信 (WeChat)** | 企业微信 / 个人微信（通过 webhook） |
| **Telegram** | Bot Token |
| **Discord** | Bot Token + Guild ID |
| **Slack** | Bot Token + Signing Secret |
| **WhatsApp** | WhatsApp Business API |
| **Signal** | Signal CLI |
| **Email** | SMTP/IMAP 配置 |
| **Matrix** | Matrix homeserver |
| **钉钉 (DingTalk)** | 企业内部群 |
| **企业微信 (WeCom)** | 企业微信群机器人 |
| **API Server** | REST API（供外部系统集成） |
| **Webhooks** | 接收外部事件 |

详细文档：[Messaging 文档](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/)

### 交互式配置

```bash
hermes gateway setup    # 交互式配置各平台
```

### 飞书接入详解

**前提条件**：
- 飞书开放平台账号
- 创建一个企业自建应用，获取 `App ID` 和 `App Secret`

**配置步骤**：
1. 在飞书开放平台创建应用，启用「机器人」能力
2. 添加权限：`im:message`、`im:message.receive_v1` 等
3. 配置事件订阅：`im.message.receive_v1`
4. 配置请求地址（Gateway URL）

**手动配置示例**：
```bash
hermes config set feishu.app_id cli_xxx
hermes config set feishu.app_secret xxx
hermes config set feishu.bot_name HermesBot
```

### 微信接入详解

企业微信渠道配置：
```bash
hermes config set weixin.corp_id your_corp_id
hermes config set weixin.corp_secret your_corp_secret
hermes config set weixin.agent_id your_agent_id
```

### Gateway 启停

```bash
hermes gateway run          # 前台运行
hermes gateway install      # 安装为后台服务（systemd）
hermes gateway start        # 启动后台服务
hermes gateway stop         # 停止服务
hermes gateway restart      # 重启服务
hermes gateway status       # 查看状态
```

**日志位置**：`~/.hermes/logs/gateway.log`

---

## 4. 记忆系统（Memory）

Hermes 支持多种记忆后端，实现跨会话持久化。

### 记忆类型

| 类型 | 说明 |
|------|------|
| **Session Memory** | 对话摘要，自动在多轮对话后写入 |
| **User Profile** | 用户身份、偏好、习惯 |
| **Skills** | 学习到的流程和经验，可跨会话复用 |
| **Session Search** | 历史会话全文搜索 |

### 配置

```yaml
memory:
  memory_enabled: true          # 启用记忆
  user_profile_enabled: true    # 启用用户画像
  provider: ""                  # 记忆提供者（空=内置）
  memory_char_limit: 2200       # 单条记忆字符上限
  user_char_limit: 1375         # 用户画像字符上限
  nudge_interval: 10            # 触发记忆写入的轮次间隔
  flush_min_turns: 6            # 最少对话轮次后才写入记忆
```

### 辅助模型配置

记忆压缩、摘要生成等任务需要调用 LLM，可配置专用模型：

```yaml
auxiliary:
  flush_memories:
    provider: auto              # auto 会自动选择可用 key
    model: ""
    api_key: ""
    timeout: 30
  session_search:
    provider: auto
    max_concurrency: 3
```

### 记忆管理命令

```bash
hermes memory status           # 查看记忆状态
hermes memory setup             # 配置记忆提供者
hermes memory off               # 关闭记忆
```

### Honcho 集成（可选）

如需更强的记忆能力，可集成 Honcho：
```bash
hermes honcho setup
hermes honcho status
```

---

## 5. Skills 系统

Skills 是 Hermes 的自学习机制——将解决过的问题、积累的工作流保存为可复用文档。

### Skill 结构

```
~/.hermes/skills/<skill-name>/
├── SKILL.md                    # Skill 定义（YAML frontmatter + Markdown）
├── references/                 # 参考文档
├── templates/                 # 模板文件
├── scripts/                    # 自动化脚本
└── assets/                    # 静态资源
```

### SKILL.md 格式

```yaml
---
name: my-skill
description: 简短描述
tags: [tag1, tag2]
---
# Skill 名称

## 触发条件
什么时候使用这个 skill

## 操作步骤
1. 步骤一
2. 步骤二

## 注意事项
- 坑点说明
```

### Skill 管理

```bash
hermes skills list              # 列出已安装 skills
hermes skills browse            # 浏览 Skills Hub
hermes skills search <query>    # 搜索 skill
hermes skills install <id>      # 安装 skill
hermes skills check             # 检查更新
hermes skills update            # 更新 skills
hermes skills config            # 配置 skills 平台启用情况
```

### 在会话中加载 Skill

```
/skill <skill-name>             # 加载 skill 到当前会话
```

或启动时预加载：
```bash
hermes -s skill1,skill2        # 预加载多个 skills
hermes --skills skill1          # 同上
```

### 外部 Skill 源

添加 GitHub 仓库作为 skill 来源：
```bash
hermes skills tap add https://github.com/user/repo
```

---

## 6. Profiles（多实例隔离）

Profiles 允许同时运行多个独立的 Hermes 实例，拥有独立的配置、会话、记忆和 skills。

### 基本操作

```bash
hermes profile list             # 列出所有 profiles
hermes profile create <name>     # 创建新 profile
hermes profile use <name>        # 设置默认 profile
hermes profile delete <name>    # 删除 profile
hermes profile show <name>      # 查看 profile 详情
```

### 克隆与导入导出

```bash
hermes profile create --clone xingruyin backup1    # 克隆现有 profile
hermes profile export <name>    # 导出为 tar.gz
hermes profile import <file>   # 从压缩包导入
```

### Profile 目录结构

```
~/.hermes/profiles/<name>/
├── config.yaml
├── sessions/
├── skills/
├── memories/
├── SOUL.md           # Agent 个性定义
├── USER.md           # 用户画像
├── MEMORY.md         # 持久记忆
└── ...
```

---

## 7. 核心配置参考

### 完整配置路径

| 配置项 | 路径 | 说明 |
|--------|------|------|
| 主配置 | `~/.hermes/config.yaml` | 全局配置 |
| 密钥 | `~/.hermes/.env` | API Key 等 |
| 会话 | `~/.hermes/sessions/` | 对话记录 |
| 日志 | `~/.hermes/logs/` | 运行日志 |
| 技能 | `~/.hermes/skills/` | 已安装 skills |
| Profile | `~/.hermes/profiles/<name>/` | 各实例独立配置 |

### 常用配置项

```yaml
# 模型
model:
  provider: custom
  base_url: https://api.minimaxi.com/anthropic
  default: MiniMax-M2.7
  api_key: sk-xxx

# Agent 行为
agent:
  max_turns: 60              # 最大对话轮次
  tool_use_enforcement: auto # 工具使用策略
  reasoning_effort: medium

# 终端
terminal:
  backend: local             # local/docker/ssh/modal
  timeout: 180

# 记忆
memory:
  memory_enabled: true
  user_profile_enabled: true

# Approvals（危险操作审批）
approvals:
  mode: manual               # manual/auto/yolo
  timeout: 60

# 日志
logging:
  level: INFO
  max_size_mb: 5
  backup_count: 3
```

---

## 8. API Server 模式

Hermes 内置 REST API Server，可供外部系统调用 Agent 能力。

### 启动

Gateway 已包含 API Server（`api_server` 状态为 `connected`），直接通过 Gateway 暴露。

独立启动：
```bash
hermes gateway run
```

### API 调用示例

```bash
# 查看 API Server 状态
curl http://localhost:8000/health

# 发送消息（需认证）
curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"message": "你好", "platform": "feishu", "chat_id": "oc_xxx"}'
```

### Webhook 订阅

```bash
hermes webhook subscribe my_hook    # 创建 /webhooks/my_hook 路由
hermes webhook list                 # 列出所有 webhook
hermes webhook test my_hook         # 发送测试请求
hermes webhook remove my_hook       # 删除 webhook
```

---

## 9. 定时任务（Cron）

### 基本操作

```bash
hermes cron list                # 列出所有定时任务
hermes cron create "30m"       # 创建每 30 分钟执行的任务
hermes cron create "0 9 * * *" # 创建每天 9:00 执行的任务
hermes cron edit <id>          # 编辑任务
hermes cron pause <id>         # 暂停任务
hermes cron resume <id>        # 恢复任务
hermes cron remove <id>        # 删除任务
```

### 创建带 Skill 的 Cron 任务

```bash
hermes cron create "every 2h" \
  --skill my-skill \
  --prompt "检查系统状态并报告"
```

---

## 10. MCP 服务器集成

MCP（Model Context Protocol）允许 Hermes 连接外部工具和服务。

### 管理 MCP 服务器

```bash
hermes mcp list                # 列出已配置的 MCP 服务器
hermes mcp add <name>          # 添加 MCP 服务器（--url 或 --command）
hermes mcp remove <name>       # 移除 MCP 服务器
hermes mcp test <name>         # 测试连接
hermes mcp configure <name>    # 配置工具选择
```

### 以 MCP Server 模式运行 Hermes

```bash
hermes mcp serve               # 将 Hermes 作为 MCP Server 运行
```

---

## 11. 常见问题

### Gateway 启动后渠道无响应

1. 检查状态：`hermes gateway status`
2. 查看日志：`tail -50 ~/.hermes/logs/gateway.log`
3. 重启渠道：gateway 中发送 `/restart`

### 模型调用失败

```bash
hermes doctor              # 检查配置完整性
hermes config check        # 检查缺失的配置项
```

### Tools / Skills 未生效

工具和技能的变更只在**新会话**生效：
- CLI：退出重进
- Gateway：发送 `/restart`

### 飞书机器人收不到消息

1. 确认事件订阅的 URL 已正确配置（Gateway 暴露的地址）
2. 检查飞书应用的权限是否包含 `im:message.receive_v1`
3. 确认机器人已被拉入群或私聊已开启

### 微信消息发送失败

企业微信需确认 `agent_id`、`corp_id`、`corp_secret` 均正确配置。

---

## 12. 部署架构示意

```
                    ┌─────────────────┐
                    │   Hermes Agent  │
                    │  (Hermes Gateway)│
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
    ┌────▼────┐        ┌─────▼─────┐       ┌────▼────┐
    │ 飞书    │        │  微信     │       │ Telegram│
    │ Feishu  │        │  WeChat   │       │         │
    └─────────┘        └───────────┘       └─────────┘

         ┌───────────────────┬───────────────────┐
         │                   │                   │
    ┌────▼────┐        ┌─────▼─────┐       ┌────▼────┐
    │ API     │        │ Webhooks  │       │ 定时任务 │
    │ Server  │        │           │       │  Cron   │
    └─────────┘        └───────────┘       └─────────┘

         ┌───────────────────┬───────────────────┐
         │                   │                   │
    ┌────▼────┐        ┌─────▼─────┐       ┌────▼────┐
    │ Skills  │        │  Memory   │       │ Sessions│
    │ 存储    │        │  记忆存储  │       │  会话   │
    └─────────┘        └───────────┘       └─────────┘

         ┌─────────────────────────────────────┐
         │           LLM Providers             │
         │  OpenRouter / Anthropic / MiniMax  │
         └─────────────────────────────────────┘
```

---

## 相关文档

- [飞书群打招呼 Skill](./messaging/feishu-group-greeting/SKILL.md)
- [Skills Hub](https://hermes-agent.nousresearch.com/docs/reference/skills-catalog)
- [Tools Reference](https://hermes-agent.nousresearch.com/docs/reference/tools-reference)
- [CLI Commands](https://hermes-agent.nousresearch.com/docs/reference/cli-commands)
