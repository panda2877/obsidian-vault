# Claude Code 安装配置完整指南

> 更新时间：2026-04-29
> 适用平台：Windows (WSL/Linux)、macOS、Linux
> Claude Code 版本：v2.x

---

## 一、简介

Claude Code 是 Anthropic 官方推出的 CLI 编程代理工具，基于 Claude 模型驱动，可独立完成代码编写、调试、重构、代码审查等任务。支持工具调用、Git 工作流、MCP 扩展、子 Agent 协作等高级特性。

**核心能力：**
- 读写文件、执行 Shell 命令、Git 操作
- 多轮交互式会话 / 单次 Print 模式
- MCP (Model Context Protocol) 工具扩展
- 子 Agent 委托与团队协作
- 代码审查、安全分析、测试生成

---

## 二、安装

### 2.1 前置要求

| 要求        | 说明                           |
| --------- | ---------------------------- |
| Node.js   | v18+（Claude Code 基于 Node.js） |
| npm / npx | 用于全局安装                       |
| Claude 账户 | Pro / Max 订阅，或 API Key       |

```bash
# 检查 Node.js 版本
node --version   # 需要 v18+

# 检查 npm 版本
npm --version
```

### 2.2 安装命令（全局安装）

```bash
npm install -g @anthropic-ai/claude-code

# 验证安装
claude --version
```

> **提示：** Linux/macOS 可使用 `sudo npm install -g ...` 获取系统级权限。Windows 推荐通过 WSL2 使用。

### 2.3 更新升级

```bash
# 方式一：CLI 内置命令
claude update

# 方式二：重新安装
npm install -g @anthropic-ai/claude-code
```

### 2.4 健康检查

```bash
claude doctor
```

检查项：自动更新器状态、安装完整性、网络连通性。

---

## 三、认证配置

Claude Code 支持三种认证方式，根据你的情况选择其一。

### 3.1 API Key 认证（推荐国内用户 / API 使用者）

```bash
# 方式一：环境变量（临时生效）
export ANTHROPIC_API_KEY="sk-ant-..."

# 方式二：写入配置文件（永久生效）
# 编辑 ~/.claude/settings.json（用户级）或项目 .claude/settings.json
```

**配置文件示例：**

```json
{
  "apiKey": "sk-ant-..."
}
```

> **国内 API 兼容配置**：若使用 OpenRouter、SiliconFlow 等兼容 Anthropic API 的转发服务，将服务提供的 API Key 填入 `ANTHROPIC_API_KEY` 环境变量即可。Claude Code 会自动识别兼容端点。

### 3.2 控制台登录（OAuth + 按量计费）

```bash
claude auth login --console
```

浏览器打开 OAuth 登录页面，完成后自动写入认证信息。适用于 Pro/Max 订阅用户。

### 3.3 企业 SSO 登录

```bash
claude auth login --sso
```

适用于企业账户。

### 3.4 认证状态查询

```bash
# 人类可读输出
claude auth status --text

# JSON 输出
claude auth status
```

---

## 四、基础配置

### 4.1 配置文件层级

Claude Code 配置遵循**优先级从高到低**：

| 优先级 | 位置 | 范围 |
|--------|------|------|
| 1 | CLI 参数 | 当前命令 |
| 2 | `.claude/settings.local.json` | 本地项目（个人，gitignore） |
| 3 | `.claude/settings.json` | 项目（团队共享，git 追踪） |
| 4 | `~/.claude/settings.json` | 用户全局 |

### 4.2 常用配置项

```json
{
  "permissions": {
    "allow": ["Bash(npm run lint:*)", "WebSearch", "Read"],
    "ask": ["Write(*.ts)", "Bash(git push*)"],
    "deny": ["Read(.env)", "Bash(rm -rf *)"]
  },
  "model": "sonnet",
  "effort": "medium"
}
```

### 4.3 CLAUDE.md 项目记忆文件

Claude Code 启动时自动加载项目根目录的 `CLAUDE.md`，用于持久化项目上下文。

```markdown
# 项目：MyAPI

## 技术栈
- FastAPI + SQLAlchemy
- PostgreSQL + Redis
- pytest（覆盖率目标 90%）

## 常用命令
- `make test` — 完整测试套件
- `make lint` — ruff + mypy

## 代码规范
- 公开函数必须添加类型注解
- Docstring 使用 Google 风格
```

**层级结构：**
- `~/.claude/CLAUDE.md` — 全局记忆（所有项目生效）
- `./CLAUDE.md` — 项目记忆（git 追踪）
- `.claude/CLAUDE.local.md` — 个人覆盖（gitignore）

### 4.4 规则目录（模块化记忆）

项目规则多时，可用规则目录替代单一大文件：

```
.claude/rules/
├── code-style.md
├── git-workflow.md
└── testing.md
```

---

## 五、使用模式

Claude Code 支持两种核心运行模式。

### 5.1 Print 模式（单次任务，推荐）

非交互式，一次性完成任务并退出。适合自动化脚本、CI/CD、单次编码任务。

```bash
# 基本用法
claude -p "修复 src/auth.py 中的登录 bug"

# 限制工具权限
claude -p "添加单元测试" --allowedTools "Read,Bash,Write" --max-turns 10

# 指定模型
claude -p "重构数据库层" --model opus --max-turns 15

# JSON 输出（适合程序解析）
claude -p "分析代码安全性" --output-format json --max-turns 5

# 费用上限
claude -p "批量重命名文件" --max-budget-usd 0.50 --max-turns 5
```

> **优势：** 无需处理 TUI 对话框、无需 tmux 编排、直接返回结构化结果。

### 5.2 交互式 REPL 模式

启动一个常驻会话，支持多轮对话、斜杠命令、人工干预。

```bash
claude
# 或直接指定任务
claude "重构 auth 模块为 JWT"

# 断点续聊（同一目录）
claude -c

# 按 ID 恢复历史会话
claude -r <session_id>
```

**常用斜杠命令：**

| 命令                 | 用途           |
| ------------------ | ------------ |
| `/compact [focus]` | 压缩上下文，保留关键信息 |
| `/review`          | 代码审查         |
| `/security-review` | 安全分析         |
| `/plan [描述]`       | 进入计划模式       |
| `/model [模型]`      | 切换模型         |
| `/effort [级别]`     | 调整推理深度       |
| `/clear`           | 清空对话历史       |
| `/context`         | 查看上下文使用率     |
| `/exit`            | 退出会话         |

---

## 六、高级用法

### 6.1 MCP 扩展集成

MCP (Model Context Protocol) 让 Claude Code 调用外部工具和服务。

```bash
# 添加 GitHub MCP 服务
claude mcp add github -- npx @modelcontextprotocol/server-github

# 添加 PostgreSQL MCP 服务
claude mcp add postgres -- npx @anthropic-ai/server-postgres --connection-string postgresql://localhost/mydb

# 列出已配置的 MCP 服务
claude mcp list

# 移除 MCP 服务
claude mcp remove <name>
```

### 6.2 子 Agent 委托

Claude Code 支持定义专用子 Agent，协同完成复杂任务。

```bash
# 在项目中创建子 Agent
# 文件：.claude/agents/security-reviewer.md
```

```markdown
---
name: security-reviewer
description: 安全代码审查
model: opus
tools: [Read, Bash]
---
你是一位资深安全工程师，专注于：
- 注入漏洞（SQL、XSS、命令注入）
- 认证/授权缺陷
- 硬编码密钥检测
- 不安全反序列化
```

使用方式：在对话中引用 `@security-reviewer`

### 6.3 Git Worktree 并行开发

```bash
# 创建隔离的 git worktree + tmux 会话
claude -w feature-x --tmux

# 直接创建 worktree（不启动 tmux）
claude -w feature-y
```

### 6.4 GitHub PR 集成

```bash
# 审查指定 PR
claude -p "全面审查这个 PR" --from-pr 42 --max-turns 10

# 对比两个分支
git diff main...feature-branch | claude -p "审查 diff，查找 bug 和安全问题"
```

### 6.5 钩子（Hooks）自动化

在特定事件触发时自动执行脚本，例如：提交前检查、代码格式化、安全扫描。

```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "Write(*.py)",
      "hooks": [{"type": "command", "command": "ruff check --fix $CLAUDE_FILE_PATHS"}]
    }],
    "PreToolUse": [{
      "matcher": "Bash",
      "hooks": [{"type": "command", "command": "if echo \"$CLAUDE_TOOL_INPUT\" | grep -q 'rm -rf'; then echo 'Blocked!' && exit 2; fi"}]
    }]
  }
}
```

---

## 七、国内 API 兼容配置（OpenRouter / SiliconFlow 等）

Claude Code 默认使用 Anthropic 官方 API。以下为国内转发服务配置方法。

### 7.1 原理说明

OpenRouter、SiliconFlow 等服务提供与 Anthropic API 兼容的端点，只需将服务提供的 API Key 和自定义 base URL 配置进去即可。

### 7.2 配置步骤

**步骤 1：获取转发服务的 API Key**

在 OpenRouter（openrouter.ai）或 SiliconFlow 等平台注册并获取 API Key。

**步骤 2：配置环境变量**

```bash
# OpenRouter 示例
export ANTHROPIC_API_KEY="sk-or-v1-..."
export ANTHROPIC_BASE_URL="https://openrouter.ai/api/v1"

# SiliconFlow 示例
export ANTHROPIC_API_KEY="sk-..."
export ANTHROPIC_BASE_URL="https://api.siliconflow.cn/v1"
```

**步骤 3：验证连通性**

```bash
claude -p "你好，请回复 TEST" --max-turns 1
```

**步骤 4：持久化配置（可选）**

写入 `~/.claude/settings.json`：

```json
{
  "apiKey": "sk-or-v1-...",
  "baseUrl": "https://openrouter.ai/api/v1",
  "model": "anthropic/claude-sonnet-4-6"
}
```

> **注意：** 国内转发服务可能不支持部分 Claude Code 特有功能（如部分 beta 特性），请以实际测试为准。

---

## 八、tmux 编排（交互模式进阶）

交互模式需要通过 tmux 进行会话管理，适合需要长时间运行、人工阶段性介入的任务。

### 8.1 基本流程

```bash
# 1. 创建 tmux 会话
tmux new-session -d -s claude-work -x 140 -y 40

# 2. 在 tmux 中启动 Claude Code
tmux send-keys -t claude-work 'cd /path/to/project && claude' Enter

# 3. 等待启动完成后发送任务（4秒后按 Enter 接受信任对话框）
sleep 4 && tmux send-keys -t claude-work Enter

# 4. 监控进度
sleep 15 && tmux capture-pane -t claude-work -p -S -50

# 5. 发送后续任务
tmux send-keys -t claude-work '添加单元测试' Enter

# 6. 退出
tmux send-keys -t claude-work '/exit' Enter
```

### 8.2 信任对话框处理

首次在目录中运行 Claude Code 会弹出信任确认：

```
❯ 1. Yes, I trust this folder
  2. No, exit
```

默认选择「Yes」，直接按 Enter 即可。

### 8.3 多任务并行

```bash
# 任务 1：修复后端
tmux new-session -d -s task1
tmux send-keys -t task1 'cd ~/project && claude -p "Fix auth bug" --allowedTools "Read,Edit" --max-turns 10' Enter

# 任务 2：写测试
tmux new-session -d -s task2
tmux send-keys -t task2 'cd ~/project && claude -p "Write integration tests" --allowedTools "Read,Write,Bash" --max-turns 15' Enter

# 统一监控
sleep 30 && for s in task1 task2; do echo "=== $s ==="; tmux capture-pane -t $s -p -S -5; done
```

---

## 九、CLI 参数速查

| 参数 | 说明 |
|------|------|
| `-p, --print` | Print 模式（单次任务） |
| `-c, --continue` | 续聊最近会话 |
| `-r, --resume <id>` | 恢复指定会话 |
| `--model <alias>` | 模型选择：`sonnet`、`opus`、`haiku` |
| `--effort <level>` | 推理深度：`low`/`medium`/`high`/`max`/`auto` |
| `--max-turns <n>` | 最大轮数（Print 模式） |
| `--max-budget-usd <n>` | 费用上限（最低 $0.05） |
| `--allowedTools <tools>` | 允许的工具列表 |
| `--dangerously-skip-permissions` | 跳过所有权限确认 |
| `--bare` | 跳过插件/钩子/MCP（最快启动） |
| `--output-format json` | JSON 结构化输出 |
| `-d, --debug [filter]` | 调试日志 |

---

## 十、常见问题

**Q：Print 模式是否会自动创建 Git 提交？**
不会。Print 模式只执行任务，不会自动提交。如需提交，请在任务描述中说明，或在交互模式下使用 `/commit`。

**Q：如何限制 Claude Code 可以访问的目录？**
在 `settings.json` 中配置 `permissions.deny` 拒绝特定路径，或在调用时指定 `--disallowedTools`。

**Q：Print 模式支持中文吗？**
支持。只要模型支持中文，Print 模式的 prompt 使用中文即可得到中文输出。

**Q：Windows 用户如何安装？**
推荐通过 WSL2（Windows Subsystem for Linux）安装，使用 Linux 安装命令即可原生运行。

**Q：国内网络访问不稳定怎么办？**
使用 OpenRouter/SiliconFlow 等国内转发服务，配合 `ANTHROPIC_BASE_URL` 环境变量配置自定义端点。

---

## 相关文档

- [[Claude Code Skill]]（Hermes Agent 集成手册）
- [[Hermes Agent主体]]
- [[AIAgent主循环]]
