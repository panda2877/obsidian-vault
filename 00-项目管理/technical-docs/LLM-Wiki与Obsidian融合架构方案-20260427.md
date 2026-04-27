---
title: LLM Wiki 与 Obsidian 融合架构方案
created: 2026-04-27
updated: 2026-04-27
tags: [wiki, obsidian, knowledge-base]
source:
---

# LLM Wiki 与 Obsidian 融合架构方案

> 日期：2026-04-27
> 版本：v1.0
> 状态：待审阅
> 负责人：银月

---

## 1. 背景与目标

当前 Obsidian Vault 已承担项目管理文档的存储职能。为进一步构建知识积累体系，引入 Karpathy LLM Wiki 模式，实现知识提炼与复用的长期价值。

**核心诉求：**
- 不做实时向量检索（RAG-alternative 路线）
- 利用 Obsidian 现有能力（wikilinks + 知识图谱）
- 原始资料与 wiki 内容共存于同一 vault
- 避免目录重复，遵循 obsidian 原生组织逻辑

---

## 2. 架构设计

### 2.1 目录结构

```
~/obsidian-vault/           ← Obsidian + Wiki 合一
├── 00-项目管理/            ← 项目管理文档
├── 01-学习/               ← 学习笔记 + 原始资料（文章/论文等）
├── 02-资源/               ← 共享资源
├── 04-临时/               ← 临时文件
└── wiki/                   ← Wiki 提炼内容
    ├── entities/           # 实体页（人物/公司/产品）
    ├── concepts/           # 概念页（方法论/技术点）
    ├── comparisons/        # 对比分析页
    ├── queries/            # 有价值的问答结果
    ├── SCHEMA.md           # Wiki 规范定义
    ├── index.md            # 内容索引
    └── log.md              # 操作日志
```

### 2.2 各层职责

| 目录 | 定位 | 管理方式 |
|------|------|---------|
| `00-项目管理/` | 项目全生命周期文档 | 思月按归档流程维护 |
| `01-学习/` | 学习笔记 + 原始资料 | 思月/如音摄入源材料 |
| `wiki/entities` | 实体提炼页 | 银月（agent）提炼 |
| `wiki/concepts` | 概念提炼页 | 银月（agent）提炼 |
| `wiki/comparisons` | 对比分析页 | 银月（agent）提炼 |

### 2.3 原始资料与 Wiki 的关系

```
原始资料（01-学习/）
    ↓ 摄入
Wiki 提炼（wiki/entities, concepts, comparisons）
    ↓ 关联
Obsidian 知识图谱（Graph View）
```

- **原始资料在原处**：文章放 `01-学习/`、项目文档放 `00-项目管理/`
- **Wiki 只存提炼后内容**：不复制原始资料，只建 wikilinks 关联
- **双向链接**：wiki 页面可链接到原始资料，原始资料也可引用 wiki 概念

---

## 3. Wiki 内容组织

### 3.1 目录说明

| 目录 | 内容 | 示例 |
|------|------|------|
| `entities/` | 实体页（人物/组织/产品/项目） | `openai.md`, `transformer.md` |
| `concepts/` | 概念页（方法论/技术点/理论） | `注意力机制.md`, `RAG替代方案.md` |
| `comparisons/` | 对比分析页 | `GPT-4 vs Claude 2.md` |
| `queries/` | 有价值的问答结果 | `如何学习LLM训练.md` |

### 3.2 命名规范

- 文件名：`小写-连字符.md`（如 `注意力机制.md`）
- 页面内必须包含 YAML frontmatter
- 页面内至少 2 个 `[[wikilinks]]` 指向其他 wiki 页面

### 3.3 Frontmatter 模板

```yaml
---
title: 页面标题
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: entity | concept | comparison | query
tags: [tag1, tag2]
sources: [原始资料路径]
---
```

---

## 4. 操作流程

### 4.1 摄入源材料

```
收到源材料（文章/论文/文档）
    ↓
存入对应目录（01-学习/ 等）
    ↓
银月提炼：创建/更新 wiki 实体或概念页
    ↓
建立 wikilinks 关联
    ↓
更新 wiki/index.md
    ↓
追加 wiki/log.md
```

### 4.2 查询知识

```
用户提问
    ↓
银月读取 wiki/index.md + 相关页面
    ↓
综合回答，引用 [[页面名]]
    ↓
如有价值，创建 queries/ 页面保存
```

---

## 5. 向量搜索规划

**当前阶段：不实现向量搜索**

理由：
1. Obsidian Vault 规模有限，内置搜索 + wikilinks 基本够用
2. Agent 直接读 wiki 页面比向量检索更准确
3. 待知识库规模增长后，再评估是否引入向量搜索

**未来扩展方向：**
- Obsidian Copilot 插件（OpenAI/Ollama embeddings）
- 外挂 ChromaDB/Qdrant 向量数据库
- 按需评估，不提前过度设计

---

## 6. 与 Obsidian 原架构的差异

| 项目 | 旧架构 | 新架构 |
|------|--------|--------|
| Wiki 结构 | 无 | 新增 `wiki/` 目录 |
| 知识积累 | 无 | LLM Wiki 模式 |
| 知识图谱 | 仅项目文档 | 全部 wiki 内容 |
| 原始资料位置 | `01-学习/` | `01-学习/`（不变） |

---

## 7. 后续计划

- [ ] 初始化 `wiki/` 目录结构
- [ ] 编写 `wiki/SCHEMA.md` 规范
- [ ] 制定知识摄入优先级
- [ ] 如有需要，评估向量搜索插件

---

*本文档由银月撰写*
*日期：2026-04-27*
