---
title: obsidian-vault-deploy-v1.0
created: 2026-04-27
updated: 2026-04-27
tags: [project, documentation]
source: 
---

# Obsidian Vault 部署方案

> 日期：2026-04-27
> 状态：待审阅
> 版本：v1.0
> 负责人：幸如音

---

## 变更记录

| 版本 | 日期 | 变更类型 | 变更摘要 | 编写者 |
|------|------|---------|---------|--------|
| v1.0 | 2026-04-27 | 新增 | Obsidian Vault 安装与 Git 配置部署方案 | 幸如音 |

---

## 1. 部署目标

在服务器（134.175.163.213）上完成 Obsidian Vault 环境搭建，配置 Git 同步方案，为后续文档迁移和知识库建设奠定基础。

---

## 2. 前置条件

### 2.1 服务器环境检查

| 检查项 | 要求 | 当前状态 |
|--------|------|---------|
| Node.js 版本 | ≥ 22.0 | v22.22.2 ✅ |
| npm 版本 | ≥ 10.0 | 10.9.7 ✅ |
| Git 版本 | ≥ 2.0 | 已安装 ✅ |
| SSH 服务 | 正常运行 | 已配置 ✅ |
| 磁盘空间 | ≥ 1GB | 充足 ✅ |

### 2.2 网络访问需求

- 服务器需可访问 GitHub（用于仓库同步）
- PC 端需可通过 SSH 访问服务器（用于 Git 操作）

---

## 3. 安装步骤

### Phase 1：Obsidian Vault 目录创建

```bash
# 创建 Obsidian 主目录
mkdir -p ~/obsidian-vault

# 创建顶级目录结构
cd ~/obsidian-vault
mkdir -p "00-项目管理"
mkdir -p "01-学习"
mkdir -p "02-资源"
mkdir -p "03-临时"

# 创建 .gitkeep 确保目录被 Git 追踪
touch "00-项目管理/.gitkeep"
touch "01-学习/.gitkeep"
touch "02-资源/.gitkeep"
touch "03-临时/.gitkeep"
```

### Phase 2：Git 仓库初始化

```bash
# 初始化 Git 仓库
cd ~/obsidian-vault
git init

# 配置 Git 用户信息
git config user.name "Hermes Agent"
git config user.email "agent@hermes.local"

# 创建 .gitignore
cat > .gitignore << 'EOF'
.obsidian/
*.vault
*.log
.DS_Store
Thumbs.db
EOF

# 初始提交
git add .
git commit -m "feat: 初始化 Obsidian Vault 目录结构"
```

### Phase 3：GitHub Remote 配置

```bash
# 添加 GitHub 远程仓库（需先在 GitHub 创建空仓库）
git remote add origin git@github.com:<username>/<repo>.git

# 或者使用 HTTPS（每次需要输入凭据）
git remote add origin https://github.com/<username>/<repo>.git

# 推送到 GitHub
git branch -M main
git push -u origin main
```

### Phase 4：服务器裸仓库创建（备选，用于 PC 端通过 SSH 拉取）

```bash
# 创建裸仓库作为中转
mkdir -p ~/git/obsidian-vault.git
cd ~/git/obsidian-vault.git
git init --bare

# 配置钩子自动更新工作仓库
cat > hooks/post-receive << 'EOF'
#!/bin/bash
GIT_WORK_TREE=/home/agentuser/obsidian-vault git checkout -f main
EOF
chmod +x hooks/post-receive
```

---

## 4. PC 端配置（待宝子本地执行）

### 4.1 安装 Obsidian

1. 下载 Obsidian：https://obsidian.md/download
2. 安装并打开

### 4.2 配置 obsidian-git 插件

1. 打开 Obsidian → 设置 → 第三方插件 → 关闭安全模式
2. 在社区插件中搜索 "obsidian-git" 并安装
3. 配置插件设置：
   - Remote repository: `git@github.com:<username>/<repo>.git`
   - Auto backup interval: 5（分钟）
   - Enable status bar: ✅

### 4.3 克隆仓库到本地

```bash
git clone git@github.com:<username>/<repo>.git ~/Obsidian/Vault
```

---

## 5. 验证方法

### 5.1 服务器端验证

```bash
# 检查目录结构
ls -la ~/obsidian-vault/

# 检查 Git 状态
cd ~/obsidian-vault && git status

# 检查 GitHub 连接
git fetch origin
```

### 5.2 PC 端验证

1. 打开 Obsidian，选择刚才克隆的仓库作为 Vault
2. 创建一篇测试笔记，保存
3. 等待 5 分钟，检查 GitHub 是否有新提交
4. 在服务器上 `git pull` 确认同步成功

---

## 6. 回滚方案

### 6.1 Git 回滚

```bash
# 查看提交历史
git log --oneline

# 回滚到上一个版本
git reset --hard HEAD^

# 强制推送到远程（慎用）
git push --force origin main
```

### 6.2 目录重建

若目录损坏，可重新克隆：

```bash
cd ~
rm -rf obsidian-vault
git clone git@github.com:<username>/<repo>.git obsidian-vault
```

---

## 7. 注意事项

1. **不要在 .obsidian 目录内编辑**，这是 Obsidian 的配置目录
2. **大型二进制文件不要放入 Vault**，会导致 Git 仓库膨胀
3. **多人编辑时注意冲突**，obsidian-git 提供了基本的冲突提示
4. **定期检查 GitHub 仓库**，确保同步正常

---

## 8. 后续步骤

- [ ] 思月文档迁移（详见《Obsidian知识库搭建技术方案》Phase 2）
- [ ] obsidian-git 插件配置
- [ ] PC 端 Vault 设置

---

*本文档由 Hermes Agent 技术团队编写*
*日期：2026-04-27*
