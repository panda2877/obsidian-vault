# LLM-Wiki 与 Obsidian 融合架构方案

**版本**：v1.1.0
**日期**：20260427
**作者**：银月
**关联项目**：Obsidian-Vault

---

## 变更记录

| 版本 | 日期 | 变更类型 | 变更摘要 | 编写者 |
|------|------|---------|---------|--------|
| v1.0 | 2026-04-27 | 新增 | 初始版本，总结16条wiki文件重命名经验 | 银月 |
| v1.1 | 2026-04-27 | 整合 | 合并《obsidian-vault-deploy-v1.0》与《Obsidian知识库搭建方案-20260426》，形成完整融合架构 | 银月 |

---

## 一、概述

### 1.1 背景

团队需要搭建一个共享知识库，实现：
- **文档集中管理**：将思月现有的项目文档迁移至 Obsidian「项目管理」目录
- **学习知识库**：新建「学习」目录，利用 LLM Wiki 模式辅助内容归纳
- **多端同步**：服务器、PC端、手机端文档实时一致

### 1.2 核心挑战

1. **服务器无 GUI**：需要在服务器命令行环境管理 Obsidian Vault
2. **多端同步**：三端（服务器/PC/手机）协作，Git 作为中转
3. **词条重命名**：文件重命名后需要同步更新所有 wikilinks 引用
4. **格式统一**：Markdown + YAML frontmatter + wikilinks 三合一

### 1.3 方案定位

本文档是 LLM-Wiki 与 Obsidian 融合的**全集方案**，涵盖：
- 部署架构（三端同步）
- 目录结构
- Git 同步方案
- LLM Wiki 与 Obsidian 配合方式
- 词条重命名流程（避坑指南）
- 中文命名规范

---

## 二、部署架构

### 2.1 三端同步架构

```
┌─────────────┐     git push      ┌──────────────────┐     git push     ┌─────────────┐
│  服务器端    │ ───────────────→  │      GitHub       │ ←────────────── │   PC / 手机  │
│  （思月操作） │                  │    （中央仓库）    │    git pull    │  （宝子操作） │
└─────────────┘                  └──────────────────┘                  └─────────────┘
```

### 2.2 各端职责

| 端 | 操作方式 | 说明 |
|----|---------|------|
| 服务器端 | 改文件 → git commit → git push | 思月直接在服务器工作目录操作，推送到 GitHub |
| PC 端 | Obsidian Git 插件 pull/push | 宝子通过 Obsidian Git 与服务器工作目录同步 |
| 手机端 | Obsidian Git 插件 pull | 宝子手机端从 GitHub pull 查看/编辑 |

### 2.3 工作流程

**服务器端（思月操作）**：
```bash
cd ~/obsidian-vault
# 修改文档...
git add .
git commit -m "feat: 描述本次变更内容"
git push origin main
```

**PC 端（宝子操作）**：
```bash
# 1. 配置 Obsidian Git 插件
#    Remote repository: agentuser@134.175.163.213:/home/agentuser/obsidian-vault
#    Branch: main

# 2. 拉取服务器最新内容
#    Obsidian Git → Pull

# 3. 编辑完成后推送
#    Obsidian Git → Commit → Push
```

---

## 三、目录结构

### 3.1 顶层结构

```
~/obsidian-vault/
├── obsidian.json              # Vault 配置
├── .obsidian/                 # Obsidian 配置（Git 忽略）
├── 00-项目管理/               # 项目文档
│   ├── todo-system/
│   │   ├── README.md
│   │   └── *.md
│   └── technical-docs/
├── 01-学习/                   # 学习知识库（LLM Wiki）
│   ├── SCHEMA.md
│   ├── index.md
│   ├── log.md
│   ├── raw/
│   │   ├── articles/
│   │   ├── papers/
│   │   └── assets/
│   ├── entities/
│   ├── concepts/
│   ├── comparisons/
│   └── queries/
├── 02-资源/                   # 共享资源
├── 03-临时/                   # 临时文件
├── 04-运维/
└── 05-wiki/                   # LLM-Wiki 知识体系（核心）
    ├── entities/              # 实体/主体
    ├── concepts/             # 概念
    ├── comparisons/          # 对比
    ├── queries/              # 问题/查询
    └── guides/               # 指南/方案
```

### 3.2 05-wiki 目录说明

| 目录 | 用途 | 示例 |
|------|------|------|
| `entities/` | 实体/主体 | `Hermes Agent主体.md`、`AIAgent主循环.md` |
| `concepts/` | 概念 | `五层架构.md`、`记忆系统.md`、`工具并行执行.md` |
| `comparisons/` | 对比分析 | `PTC_vs_普通工具调用对比.md`、`Hermes_vs_OpenClaw对比.md` |
| `queries/` | 问题/查询 | `适配器模式设计取舍.md`、`中文PromptInjection检测盲区.md` |
| `guides/` | 指南/方案 | `LLM-Wiki与Obsidian融合架构方案.md` |

---

## 四、Git 同步方案

### 4.1 方案选型

**推荐方案：obsidian-git 插件 + GitHub 中转**

- 服务器初始化 Git 仓库，PC 端使用 obsidian-git 插件
- 通过 GitHub 中转同步
- 服务器作为 Git 远程仓库

### 4.2 服务器端设置

```bash
# 创建工作目录
mkdir -p ~/obsidian-vault
cd ~/obsidian-vault

# 初始化 Git
git init
git remote add origin git@github.com:panda2877/obsidian-vault.git

# 连接 GitHub
git push -u origin main
```

### 4.3 注意事项

1. **服务器直接操作工作目录**，无需 hook 或 bare 仓库中转
2. **不要在 .obsidian 目录内编辑**，这是 Obsidian 的配置目录
3. **大型二进制文件不要放入 Vault**，会导致 Git 仓库膨胀
4. **多人编辑时注意冲突**，obsidian-git 提供了基本的冲突提示
5. **PC/手机端 push 前先 pull**，避免冲突覆盖

### 4.4 常见问题

**Q: PC 端 push 失败，显示 "remote not found"？**
**A:** 检查 Obsidian Git 插件的 Remote repository 配置是否为：
```
agentuser@134.175.163.213:/home/agentuser/obsidian-vault
```

**Q: 出现冲突怎么办？**
**A:** 先 `git stash` 暂存本地修改，再 `pull`，然后 `git stash pop` 合并，最后手动解决冲突后提交。

---

## 五、LLM Wiki 与 Obsidian 配合

### 5.1 天然互补

| llm-wiki 特性 | Obsidian 集成 |
|--------------|--------------|
| Markdown 文件存储 | ✅ 原生支持 |
| `[[wikilinks]]` 跨页引用 | ✅ 内置支持 |
| YAML frontmatter | ✅ 支持 |
| raw/ 层（原始资料） | ✅ 附件文件夹 |
| 三层目录结构 | ✅ 文件夹组织 |
| Graph View 可视化 | ✅ 内置插件 |

### 5.2 分工建议

| 角色 | 操作 |
|------|------|
| LLM Wiki Agent | 负责读取 raw/ 中的资料，归纳写入 entities/concepts |
| 思月/团队成员 | 通过 Obsidian PC客户端浏览、编辑 |
| obsidian-git | 同步 PC 与服务器的变更 |

### 5.3 Wikilinks 使用规范

**格式**：`[[目标文件名]]`（不含 `.md` 扩展名）

✅ 正确：`[[Hermes Agent主体]]`
❌ 错误：`[[Hermes Agent主体.md]]`

---

## 六、中文命名规范（Obsidian Wiki）

为保证 Obsidian 兼容性和可读性，必须遵循以下规范：

| 类别 | 格式 | 示例 |
|------|------|------|
| 主体/实体 | `名称+类型` | `Hermes Agent主体`、`AIAgent主循环` |
| 概念 | 简洁中文词组 | `五层架构`、`记忆系统`、`工具并行执行` |
| 对比 | `A_vs_B对比` | `PTC_vs_普通工具调用对比`、`Hermes_vs_OpenClaw对比` |
| 查询/问题 | `问题类型-描述` | `适配器模式设计取舍`、`中文PromptInjection检测盲区` |

**禁止**：
- ❌ 空格：`Hermes Agent 主体`（Obsidian wikilink 识别问题）
- ❌ 特殊字符：`#`、`*`、`?` 等
- ❌ 超长文件名（建议 ≤ 30 字符）

---

## 七、词条重命名流程（避坑指南）

### 7.1 核心挑战

文件重命名后，需要同步更新所有文档中的 wikilinks 引用，避免图谱链接断裂。

### 7.2 推荐方案：分步执行

```bash
# Step 1: 批量重命名文件（保留扩展名）
mv hermes-agent.md "Hermes Agent主体.md"
mv base-platform-adapter.md "BasePlatformAdapter平台适配器.md"
# ... 其他文件

# Step 2: 一次性 git add（利用 rename detection）
git add -A

# Step 3: 提交
git commit -m 'rename: 16条wiki文件重命名为中文文件名，并更新wikilinks'
```

**优势**：
- 避免文件名大小写问题（macOS/Linux 文件系统默认大小写不敏感）
- 暂存后 git 自动检测 rename，操作更安全
- 支持批量处理

> ⚠️ 注意：`git mv` 在大小写不敏感文件系统上可能出问题，建议使用分步方案。

### 7.3 Wikilinks 同步策略

**替换规则**：
| 原格式 | 新格式 |
|--------|--------|
| `[[hermes-agent]]` | `[[Hermes Agent主体]]` |
| `[[ptc-vs-normal-toolcall]]` | `[[PTC_vs_普通工具调用对比]]` |

**处理流程**：
1. 重命名之前：全局搜索 `[[英文名]]` 格式，列出所有引用位置
2. 重命名之后：批量替换为 `[[中文名]]`
3. 提交时确保所有引用同步更新

### 7.4 关键要点

| 序号 | 要点 | 说明 |
|------|------|------|
| 1 | **暂存和提交分开** | 用 `git add -A` 暂存所有 rename，让 git 自动检测 |
| 2 | **Wikilinks 不含扩展名** | 替换时注意：`[[hermes-agent]]` 而非 `[[hermes-agent.md]]` |
| 3 | **批量替换前先备份** | 建议 `git commit` 后再做大规模替换 |
| 4 | **中文文件名加下划线** | `Hermes Agent主体` → `[[Hermes Agent主体]]`，Obsidian 兼容性更好 |
| 5 | **PTC vs 对比类命名** | 用 `_vs_` 分隔，如 `PTC_vs_普通工具调用对比` |

### 7.5 避坑指南

- **大小写问题**：直接 `git mv A.md B.md` 在 macOS 上可能失败，用分步方案
- **引用遗漏**：替换后检查是否有遗漏，全局搜索原文件名确认
- **图谱断链**：重命名后打开 Obsidian 图谱视图验证链接是否正常

### 7.6 标准化流程图

```
LLM-Wiki 词条重命名流程
│
├── 1. 准备阶段
│   ├── 确认旧文件名列表
│   └── 确认新文件名列表（中文命名规范）
│
├── 2. Wikilinks 扫描
│   ├── 搜索所有 [[旧文件名]] 引用
│   └── 列出受影响文档清单
│
├── 3. 文件重命名
│   ├── 批量 mv 重命名
│   ├── git add -A 暂存
│   └── git commit
│
├── 4. Wikilinks 更新
│   ├── 批量替换所有引用
│   └── git commit
│
└── 5. 验证阶段
    ├── Obsidian 图谱视图检查
    └── 全局搜索旧文件名（应为0结果）
```

---

## 八、变更记录

### v1.1.0 - 20260427
**变更摘要**：整合《obsidian-vault-deploy-v1.0》与《Obsidian知识库搭建方案-20260426》，形成完整融合架构方案
**变更内容**：
- 新增第二章「部署架构」：三端同步架构、各端职责、工作流程
- 新增第三章「目录结构」：完整目录规范
- 新增第四章「Git 同步方案」：obsidian-git 方案、注意事项、常见问题
- 新增第五章「LLM Wiki 与 Obsidian 配合」：分工建议、Wikilinks 使用规范
- 保留原第六-七章作为核心操作指南

### v1.0.0 - 20260427
**变更摘要**：初始版本，总结 LLM-Wiki 文件重命名与 Obsidian wikilinks 同步经验
**关联任务**：Obsidian Vault 16条wiki文件重命名为中文文件名

---

## 九、关联文档

- [Obsidian Vault 仓库](https://github.com/panda2877/obsidian-vault)
- wiki 文件目录：`05-wiki/entities/`、`05-wiki/concepts/`、`05-wiki/comparisons/`、`05-wiki/queries/`
- 部署方案：`00-项目管理/technical-docs/obsidian-vault-deploy-v1.0.md`（已合并入本文档）
- 搭建方案：`00-项目管理/technical-docs/Obsidian知识库搭建方案-20260426.md`（已合并入本文档）

---

*本文档由 Hermes Agent 文档团队维护*
*最后更新：2026-04-27 银月*
