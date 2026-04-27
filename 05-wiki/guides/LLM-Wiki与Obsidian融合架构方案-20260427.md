# LLM-Wiki 与 Obsidian 融合架构方案

**版本**：v1.0.0  
**日期**：20260427  
**作者**：银月  
**关联项目**：Obsidian-Vault  

---

## 变更摘要

本次成功完成 16 条 wiki 文件的英文名→中文名重命名，并同步更新了所有文档中的 wikilinks 引用，验证了 LLM-Wiki 词条管理流程的可行性。

---

## 一、任务背景

Obsidian Vault 中的 wiki 文件原为英文命名：
- `hermes-agent.md` → `Hermes Agent主体.md`
- `ptc-vs-normal-toolcall.md` → `PTC_vs_普通工具调用对比.md`
- ……共 16 条

**核心挑战**：文件重命名后，需要同步更新所有文档中的 wikilinks 引用（`[[Hermes Agent]]` → `[[Hermes Agent主体]]`），避免图谱链接断裂。

---

## 二、技术方案

### 2.1 重命名策略

**推荐方案：分步执行**

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

**备选方案：`git mv` 一次性完成**

```bash
git mv hermes-agent.md "Hermes Agent主体.md"
```

> ⚠️ 注意：`git mv` 在大小写不敏感文件系统上可能出问题，建议使用分步方案。

### 2.2 Wikilinks 同步策略

Wikilinks 格式：`[[目标文件名]]`（不含 `.md` 扩展名）

**重命名前的文档**：
```markdown
参见 [[Hermes Agent]] 和 [[BasePlatformAdapter]] 的详细说明。
```

**重命名后的文档**：
```markdown
参见 [[Hermes Agent主体]] 和 [[BasePlatformAdapter平台适配器]] 的详细说明。
```

**处理流程**：
1. 重命名之前：全局搜索 `[[英文名]]` 格式，列出所有引用位置
2. 重命名之后：批量替换为 `[[中文名]]`
3. 提交时确保所有引用同步更新

**替换规则**：
| 原格式 | 新格式 |
|--------|--------|
| `[[hermes-agent]]` | `[[Hermes Agent主体]]` |
| `[[ptc-vs-normal-toolcall]]` | `[[PTC_vs_普通工具调用对比]]` |

---

## 三、经验总结

### 3.1 关键要点

| 序号 | 要点 | 说明 |
|------|------|------|
| 1 | **暂存和提交分开** | 用 `git add -A` 暂存所有 rename，让 git 自动检测 |
| 2 | **Wikilinks 不含扩展名** | 替换时注意：`[[hermes-agent]]` 而非 `[[hermes-agent.md]]` |
| 3 | **批量替换前先备份** | 建议 `git commit` 后再做大规模替换 |
| 4 | **中文文件名加下划线** | `Hermes Agent主体` → `[[Hermes Agent主体]]`，Obsidian 兼容性更好 |
| 5 | **PTC vs 对比类命名** | 用 `_vs_` 分隔，如 `PTC_vs_普通工具调用对比` |

### 3.2 避坑指南

- **大小写问题**：直接 `git mv A.md B.md` 在 macOS 上可能失败，用分步方案
- **引用遗漏**：替换后检查是否有遗漏，全局搜索原文件名确认
- **图谱断链**：重命名后打开 Obsidian 图谱视图验证链接是否正常

### 3.3 流程标准化建议

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

## 四、中文命名规范（Obsidian Wiki）

为保证 Obsidian 兼容性和可读性，建议遵循以下规范：

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

## 五、变更记录

### v1.0.0 - 20260427
**变更摘要**：初始版本，总结 LLM-Wiki 文件重命名与 Obsidian wikilinks 同步经验  
**关联任务**：Obsidian Vault 16条wiki文件重命名为中文文件名  
**变更内容**：
- 建立 LLM-Wiki 与 Obsidian 融合架构方案
- 记录文件重命名技术方案（分步执行策略）
- 记录 Wikilinks 同步策略与替换规则
- 总结避坑指南与流程标准化建议
- 制定 Obsidian Wiki 中文命名规范

---

## 六、关联文档

- [Obsidian Vault 仓库](https://github.com/panda2877/obsidian-vault)
- wiki 文件目录：`05-wiki/entities/`、`05-wiki/concepts/`、`05-wiki/comparisons/`、`05-wiki/queries/`
