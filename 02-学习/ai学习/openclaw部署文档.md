# OpenClaw 部署文档

## 简介

OpenClaw 是开源 AI 助手平台，支持通过模块化 Skill 实现文件管理、网络搜索、任务自动化、代码开发等功能。

**核心优势：**
- 模块化 Skill 生态，灵活扩展
- 自动化任务执行，提升效率
- 支持本地/云端多种部署方式

---

## 系统要求

| 项目 | 要求 |
|------|------|
| 操作系统 | Linux (Ubuntu 22.04 LTS)、MacOS 12+、Windows 11 (需 WSL2) |
| Node.js | ≥ 22.0.0 LTS (推荐 22.10.0) |
| Git | ≥ 2.40.0 |
| 内存 | ≥ 4GB (推荐 8GB) |
| 存储 | ≥ 1GB |

---

## 部署前准备

### 1. 配置 npm 国内镜像（避免依赖下载超时）

```bash
npm config set registry https://registry.npmmirror.com
npm config get registry  # 验证
```

### 2. 安装基础依赖

**Ubuntu:**
```bash
sudo apt update && sudo apt upgrade -y
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs git
```

**MacOS:**
```bash
brew install node@22 git
```

**Windows 11 (WSL2):**
```powershell
# 管理员模式 PowerShell
wsl --install -d Ubuntu-22.04
```

---

## Linux 服务器部署

```bash
# 全局安装 OpenClaw
npm install -g openclaw

# 验证安装
openclaw --version

# 初始化配置（交互式引导，设置工作目录 ~/.openclaw）
openclaw init

# 启动服务
openclaw start
```

### 配置开机自启

```bash
sudo tee /etc/systemd/system/openclaw.service <<EOF
[Unit]
Description=OpenClaw Gateway Service
After=network.target

[Service]
User=$USER
ExecStart=$(which openclaw) start
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable openclaw
```

### 访问验证

浏览器访问：`http://<服务器公网IP>:18789`

---

## Windows 11 本地部署（WSL2）

1. 安装 WSL2（见上方「部署前准备」）
2. 在 Ubuntu 子系统中执行：

```bash
npm config set registry https://registry.npmmirror.com
npm install -g openclaw
openclaw init
openclaw start
```

3. 访问验证：`http://127.0.0.1:18789`

---

## 大模型 API 配置

### 阿里云百炼平台配置示例

1. 获取 API-Key：登录阿里云百炼 → 密钥管理 → 创建 API-Key
2. 配置 OpenClaw：

```bash
openclaw configure
# 按提示选择「阿里云千问」，输入 API-Key 与 AccessKey Secret

# 或手动配置
openclaw config set model.provider bailian
openclaw config set model.model bailian/qwen3-mini

# 重启生效
openclaw restart

# 测试连接
openclaw model test
```

---

## 定时任务配置

编辑 `~/.openclaw/tasks.json`：

```json
{
  "tasks": [
    {
      "name": "每日数据备份",
      "schedule": "0 2 * * *",
      "action": "file backup --input ~/Work --output ~/Backup --type full",
      "enabled": true
    },
    {
      "name": "网站健康检查",
      "schedule": "*/30 * * * *",
      "action": "monitor --url https://example.com --alert email",
      "enabled": true
    }
  ]
}
```

### 任务管理命令

```bash
openclaw task list          # 列出所有定时任务
openclaw task run "任务名"   # 手动触发
openclaw task disable "任务名"  # 禁用任务
```

---

## 性能优化

### 启用缓存

编辑 `~/.openclaw/config.json`：

```json
{
  "cache": {
    "enabled": true,
    "ttl": 3600,
    "maxSize": "100MB"
  }
}
```

### 并发控制

```bash
openclaw config set system.concurrency.limit 5    # 限制同时运行任务数
openclaw config set system.task.timeout 30         # 任务超时 30 秒
```

---

## 安全加固

```bash
# 禁用系统命令执行（非必要场景）
openclaw config set skills.exec.enable false

# 限制文件读写目录
openclaw config set skills.file.allowed-paths ["~/Documents", "~/Work"]

# 加密 API 密钥
openclaw config encrypt --key model.apiKey --password "你的安全密码"

# 启用操作日志审计
openclaw config set system.logging.audit true
```

---

## 监控与告警

```bash
openclaw config set monitoring.enabled true
openclaw config set monitoring.metrics ["response_time", "error_rate", "skill_usage"]

# 错误率告警（超过 5% 触发邮件通知）
openclaw config set monitoring.alerts '[{"type": "error_rate", "threshold": 5, "channels": ["email"]}]'

# 启用任务重试
openclaw config set system.task.retry.count 3
```

---

## 常见问题

### 部署问题

**Q: `openclaw --version` 提示 "command not found"**
- 检查 Node.js 版本：`node -v`（需 ≥ 22.0.0）
- 重新安装：`npm install -g openclaw --force`
- 添加环境变量：`export PATH="$(npm config get prefix)/bin:$PATH"`

**Q: 部署后无法访问控制台**
- 检查安全组是否开放 18789 端口
- 确认服务运行：`openclaw status`
- 访问地址使用服务器公网 IP，非 127.0.0.1

### Skill 问题

**Q: Skill 加载失败，提示 "依赖缺失"**
```bash
cd ~/.openclaw/skills/技能名称 && npm install
openclaw skill update 技能名称
```

**Q: 模型测试提示 "连接超时"**
- 验证 API-Key 正确且未过期
- 测试网络：`curl <模型调用地址>`
- 国内用户如使用海外模型需配置代理

---

*最后更新：2026-04-29*
