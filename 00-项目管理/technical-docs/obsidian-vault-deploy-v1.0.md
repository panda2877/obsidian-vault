---
title: obsidian-vault-deploy-v1.0
created: 2026-04-27
updated: 2026-04-27
tags: [project, documentation]
source:
---

# Obsidian Vault 部署方案

> 日期：2026-04-27
> 状态：已定稿
> 版本：v1.0
> 负责人：文思月

---

## 变更记录

| 版本 | 日期 | 变更类型 | 变更摘要 | 编写者 |
|------|------|---------|---------|--------|
| v1.0 | 2026-04-27 | 新增 | Obsidian Vault 安装与 Git 同步方案 | 幸如音 |
| v1.1 | 2026-04-27 | 更新 | 精简工作流，移除 bare 仓库方案，确立三端同步架构 | 文思月 |

---

## 1. 部署目标

建立稳定、高效的 Obsidian Vault 三端同步体系，确保服务器、PC端、手机端文档实时一致。

---

## 2. 同步架构

```
┌─────────────┐     git push      ┌──────────────────┐     git push     ┌─────────────┐
│  服务器端    │ ───────────────→  │      GitHub       │ ←────────────── │   PC / 手机  │
│  （思月操作） │                  │    （中央仓库）    │    git pull    │  （宝子操作） │
└─────────────┘                  └──────────────────┘                  └─────────────┘
```

### 2.1 各端职责

| 端 | 操作方式 | 说明 |
|----|---------|------|
| 服务器端 | 改文件 → git commit → git push | 思月直接在服务器工作目录操作，推送到 GitHub |
| PC 端 | Obsidian Git 插件 pull/push | 宝子通过 Obsidian Git 与服务器工作目录同步 |
| 手机端 | Obsidian Git 插件 pull | 宝子手机端从 GitHub pull 查看/编辑 |

---

## 3. 工作流程

### 3.1 服务器端（思月操作）

```bash
# 1. 进入工作目录
cd ~/obsidian-vault

# 2. 修改文档...

# 3. 提交变更
git add .
git commit -m "feat: 描述本次变更内容"

# 4. 推送到 GitHub
git push origin main
```

### 3.2 PC 端（宝子操作）

```bash
# 1. 配置 Obsidian Git 插件
#    Remote repository: agentuser@134.175.163.213:/home/agentuser/obsidian-vault
#    Branch: main

# 2. 拉取服务器最新内容
#    Obsidian Git → Pull

# 3. 编辑完成后推送
#    Obsidian Git → Commit → Push
```

### 3.3 手机端（宝子操作）

```bash
# 配置同 PC 端，每次查看前点 Pull 拉取最新内容
```

---

## 4. 目录结构

```
~/obsidian-vault/
├── 00-项目管理/
│   └── technical-docs/
│       └── obsidian-vault-deploy-v1.0.md   # 本文档
├── 01-学习/
├── 02-资源/
├── 03-临时/
└── .git/                                    # 工作目录 Git（非 bare 仓库）
```

---

## 5. 注意事项

1. **服务器直接操作工作目录**，无需 hook 或 bare 仓库中转
2. **不要在 .obsidian 目录内编辑**，这是 Obsidian 的配置目录
3. **大型二进制文件不要放入 Vault**，会导致 Git 仓库膨胀
4. **多人编辑时注意冲突**，obsidian-git 提供了基本的冲突提示
5. **PC/手机端 push 前先 pull**，避免冲突覆盖

---

## 6. 验证方法

### 6.1 服务器端验证

```bash
# 检查 Git 状态
cd ~/obsidian-vault && git status

# 检查提交历史
git log --oneline -3

# 验证 GitHub 连接
git fetch origin
```

### 6.2 PC/手机端验证

1. 打开 Obsidian，选择 Vault
2. 点击 Obsidian Git → Pull，确认无报错
3. 查看文档是否为最新版本

---

## 7. 常见问题

### Q: PC 端 push 失败，显示 "remote not found"？
**A:** 检查 Obsidian Git 插件的 Remote repository 配置是否为：
```
agentuser@134.175.163.213:/home/agentuser/obsidian-vault
```

### Q: 出现冲突怎么办？
**A:** 先 `git stash` 暂存本地修改，再 `pull`，然后 `git stash pop` 合并，最后手动解决冲突后提交。

---

*本文档由 Hermes Agent 文档团队编写*
*最后更新：2026-04-27 文思月*
