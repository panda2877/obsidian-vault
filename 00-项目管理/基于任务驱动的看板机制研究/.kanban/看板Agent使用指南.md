# 看板 Agent 使用指南

> 本文档面向 Agent，定义如何使用 Obsidian + SQLite 双层看板架构。
> **进度统计以 SQLite 为准，任务详情查看 Obsidian。**

---

## 一、架构说明

```
SQLite (~/.hermes/kanban.db)
└── tasks 表        ← 进度统计权威源（总数、done/backlog 计数）
└── checkpoints 表  ← 各任务最新阶段快照

Obsidian vault
└── backlog/        ← 待办任务文件
└── done/           ← 已完成任务文件
└── {in-progress,review}/  ← 进行中/审查中
└── .kanban/看板开发任务.md  ← 进度总览文档（由 sync 脚本维护）
```

**重要原则**：
- 进度聚合数字（多少 done，多少 backlog）→ 查 SQLite
- 任务详情（目标、checkpoints、阻塞原因）→ 读 Obsidian .md 文件
- 二者通过 `kanban-sync` skill 中的脚本同步

---

## 二、新建看板

### 2.1 判断是否需要建看板任务

参见 `kanban-orchestrator` skill — **判断是否建看板 vs 直接执行**。

适合建看板任务的场景（满足任一）：
1. 需要多角色协作（研究 + 分析 + 写作 = 多个 profile）
2. 工作需要跨越 crash/restart 持久化
3. 需要人工介入环节
4. 可并行执行的子任务
5. 需要 review/迭代
6. 审计追踪重要

不满足以上 → 用 `delegate_task` 或直接执行。

### 2.2 任务分解与创建

参见 `kanban-orchestrator` skill — **Decomposition Playbook**。

标准流程：
1. 画任务图（T1 → T2 → T3），确认依赖关系
2. 用 `kanban_create()` 创建所有任务，指定 `parents=[]` 或 `parents=[t1, t2]`
3. 用 `kanban_complete(summary=..., metadata=...)` 标记自己完成
4. 上报给用户

### 2.3 整体看板总览文档模板

路径：`.kanban/{project-name}-看板总览.md`

```markdown
# {项目名称} 看板

> 创建：{YYYY-MM-DD}
> 负责人：{owner}

---

## ⚠️ 重要变更：部分任务已废弃

（随项目进展更新）

---

## 进度总览

 | 阶段 | 总数 | ✅ Done | 🔄 In Progress | 📋 Backlog | 🔴 Blocked | ❌ 废弃 |
|------|------|---------|----------------|------------|------------|---------|
| P0 — {名称} | {N} | {N} | {N} | {N} | {N} | {N} |
| P1 — {名称} | {N} | {N} | {N} | {N} | {N} | {N} |
| **合计** | **{N}** | **{N}** | {N} | **{N}** | {N} | **{N}** |

**整体进度：{done}/{total}（{pct}%）**（排除废弃任务后）

---

## 任务卡片目录

### P0 — {名称}

| ID | 标题 | 负责人 | 状态 | 说明 |
|----|------|--------|------|------|
| TSK-{date}-001 | [[backlog/TSK-{date}-001|{标题}]] | {owner} | 📋 backlog | {说明} |

### P1 — {名称}

（同上格式）

---

## 目录结构

```
{project-name}/
├── .kanban/                  # 元数据
│   └── {project-name}-看板总览.md
├── backlog/                  # 待办
│   └── TSK-{date}-001.md ~ TSK-{date}-010.md
├── in-progress/              # 进行中
├── review/                   # 待审查
└── done/                     # 已完成
```

---

## 核心参考文档

- [[看板机制与原生v0.12整合方案]]
- [[看板Agent使用指南]]（本文档）
```

### 2.4 任务卡片模板

路径：`templates/task-template.md`（放在项目 templates/ 目录下）

```markdown
---
id: {{TASK_ID}}
title: {{TASK_TITLE}}
status: {{STATUS}}           # inbox | in_progress | review | done
priority: {{PRIORITY}}       # P0 | P1 | P2 | P3
assignee: {{ASSIGNEE}}
mission_id: {{MISSION_ID}}
created: {{CREATED_AT}}      # ISO 8601
updated: {{UPDATED_AT}}     # ISO 8601
---

## 任务目标

{{TASK_GOAL}}

## 检查点历史

{{CHECKPOINT_HISTORY}}

---

## 笔记

{{NOTES}}
```

### 2.5 新建任务到 SQLite

参见 `kanban-worker` skill — **State Reconciliation: Obsidian vs SQLite**。

**注意**：优先使用 `kanban_create()` tool/script 建任务，SQLite INSERT 仅在 tool 不可用时兜底。

```python
# 兜底方案（tool 不可用时）
import sqlite3
from datetime import datetime, timezone

conn = sqlite3.connect('/home/agentuser/.hermes/kanban.db')
cur = conn.cursor()
cur.execute("""
    INSERT INTO tasks (id, title, body, assignee, status, priority, created_by, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
""", (
    'TSK-YYYYMMDD-NNN',
    '任务标题',
    '任务目标内容',
    'xingruyin',   # profile 名，不是 agent_id
    'backlog',
    1,              # P1=1
    'xingruyin',
    int(datetime.now(timezone.utc).timestamp())
))
conn.commit()
conn.close()
```

### 2.6 链接规范

| 链接类型 | 格式 | 示例 |
|---------|------|------|
| 任务卡片相互链接 | `[[backlog/TSK-20260504-001\|标题]]` | 任务目录页链接到具体卡片 |
| 主文档链接任务卡片 | `[[backlog/TSK-20260504-001\|[P0] 任务标题]]` | 看板总览链接到任务 |
| 跨文档交叉引用 | `[[看板开发任务#P0 — 核心闭环]]` | 方案文档引用看板章节 |

### 2.7 Git 提交

```bash
cd /home/agentuser/obsidian-vault
git add "00-项目管理/{project}/backlog/TSK-YYYYMMDD-NNN.md"
git commit -m "feat(kanban): 新建任务 TSK-YYYYMMDD-NNN"
git push
```

---

## 三、查询待办

**使用 `kanban-todo` skill。**

加载 skill 后有两种方式：

```bash
# 方式一：直接执行脚本（推荐）
python3 /home/agentuser/.hermes/skills/kanban-todo/scripts/kanban_todo.py
```

```python
# 方式二：直接写 Python 查询
import sqlite3
conn = sqlite3.connect('/home/agentuser/.hermes/kanban.db')
cur = conn.cursor()

# 按状态统计（权威数字）
cur.execute("""
    SELECT status, COUNT(*) as cnt
    FROM tasks
    WHERE id LIKE 'TSK-%'
    GROUP BY status
""")
for row in cur.fetchall():
    print(f"{row[0]}: {row[1]}")

conn.close()
```

**陷阱**：assignee 存的是 **profile 名**（如 `xingruyin`），不是 `agent-xingruyin`。

---

## 四、更新看板进度

### 4.1 完成任务标准流程

参见 `kanban-worker` skill — **Task Completion Checklist**。

**核心原则**：`kanban-sync` skill 同步 SQLite → Obsidian；手动补 Git 提交。

### 4.2 步骤一：更新 SQLite 状态

```python
import sqlite3
from datetime import datetime, timezone

conn = sqlite3.connect('/home/agentuser/.hermes/kanban.db')
cur = conn.cursor()

task_id = 'TSK-YYYYMMDD-NNN'

# 更新任务状态
cur.execute("""
    UPDATE tasks
    SET status = 'done',
        completed_at = ?
    WHERE id = ?
""", (int(datetime.now(timezone.utc).timestamp()), task_id))

# 写入 final checkpoint
cur.execute("""
    INSERT INTO checkpoints (id, task_id, phase, summary, agent_id, created_at)
    VALUES (?, ?, ?, ?, ?, ?)
""", (
    f'{task_id}-final',
    task_id,
    'done',
    '任务已完成，所有目标达成',
    'xingruyin',
    datetime.now(timezone.utc).isoformat()
))

conn.commit()
conn.close()
```

### 4.3 步骤二：迁移 Obsidian 文件

```python
import shutil, re, os
from datetime import datetime, timezone

task_id = 'TSK-YYYYMMDD-NNN'
project = '{project}'
vault = '/home/agentuser/obsidian-vault'

old_path = f"{vault}/00-项目管理/{project}/backlog/{task_id}.md"
new_path = f"{vault}/00-项目管理/{project}/done/{task_id}.md"

# 迁移文件
os.makedirs(f"{vault}/00-项目管理/{project}/done", exist_ok=True)
shutil.move(old_path, new_path)

# 更新 frontmatter
with open(new_path, 'r') as f:
    content = f.read()

content = re.sub(r'^status: .+$', 'status: done', content, flags=re.MULTILINE)
content = re.sub(r'^updated: .+$', f'updated: {datetime.now(timezone.utc).isoformat()}', content, flags=re.MULTILINE)

with open(new_path, 'w') as f:
    f.write(content)
```

### 4.4 步骤三：Git 提交

```bash
cd /home/agentuser/obsidian-vault
git add "00-项目管理/{project}/done/{task_id}.md"
git commit -m "done(kanban): 完成任务 {task_id}"
git push
```

### 4.5 同步进度总览文档

参见 `kanban-sync` skill — **进度总览自动维护**。

由 sync 脚本自动更新 `看板开发任务.md`。手动更新时：

```python
import re

doc_path = '/home/agentuser/obsidian-vault/00-项目管理/基于任务驱动的看板机制研究/看板开发任务.md'

with open(doc_path, 'r') as f:
    content = f.read()

# 替换合计行（基于 SQLite 查询的真实数字）
# 替换进度行
content = re.sub(
    r'\*\*整体进度：.*?\*\*',
    f'**整体进度：{done}/{total}（{pct}%）**（排除废弃任务后）',
    content
)

with open(doc_path, 'w') as f:
    f.write(content)
```

---

## 五、查看任务详情

### 5.1 读 Obsidian 任务卡片

```python
import glob

def find_task_file(task_id: str) -> str:
    """根据 task_id 找到对应的 .md 文件"""
    vault = '/home/agentuser/obsidian-vault'
    for subdir in ['backlog', 'done', 'in-progress', 'review']:
        pattern = f"{vault}/00-项目管理/*/{subdir}/{task_id}.md"
        matches = glob.glob(pattern)
        if matches:
            return matches[0]
    return None

path = find_task_file('TSK-YYYYMMDD-NNN')
with open(path, 'r') as f:
    content = f.read()
# content 包含 frontmatter + 任务目标 + 检查点历史 + 笔记
```

### 5.2 查 checkpoints 历史（SQLite）

```python
import sqlite3
conn = sqlite3.connect('/home/agentuser/.hermes/kanban.db')
cur = conn.cursor()

cur.execute("""
    SELECT c.phase, c.summary, c.blockers, c.next_steps, c.created_at
    FROM checkpoints c
    WHERE c.task_id = ?
    ORDER BY c.created_at ASC
""", (task_id,))

for row in cur.fetchall():
    print(f"[{row[4]}] {row[0]}: {row[1]}")
    if row[2]:
        print(f"  ⚠️ 阻塞: {row[2]}")
    if row[3]:
        print(f"  → 下一步: {row[3]}")

conn.close()
```

---

## 六、常见操作速查

| 操作 | 方法 |
|------|------|
| 新建看板任务 | 加载 `kanban-orchestrator` → `kanban_create()` |
| 查询待办列表 | 加载 `kanban-todo` → 执行脚本或 SQLite 查询 |
| 完成任务 | 加载 `kanban-worker` → SQLite 更新 + 文件迁移 + Git |
| 同步进度总览 | 加载 `kanban-sync` → 执行 sync.py |
| 查看任务详情 | 读 Obsidian .md + SQLite checkpoints |
| 查整体进度统计 | SQLite: `SELECT status, COUNT(*) FROM tasks GROUP BY status` |

---

## 七、路径速查

| 资源 | 路径 |
|------|------|
| SQLite 数据库 | `/home/agentuser/.hermes/kanban.db` |
| Obsidian vault 根目录 | `/home/agentuser/obsidian-vault/` |
| 看板总览文档 | `00-项目管理/基于任务驱动的看板机制研究/.kanban/{project}-看板总览.md` |
| 任务卡片 | `00-项目管理/{project}/{status}/TSK-{date}-{seq}.md` |
| 任务模板 | `00-项目管理/{project}/templates/task-template.md` |
| kanban-todo 脚本 | `/home/agentuser/.hermes/skills/kanban-todo/scripts/kanban_todo.py` |
| kanban-sync 脚本 | `/home/agentuser/.hermes/skills/kanban-sync/scripts/sync.py` |

---

## 八、禁止事项

1. **不要**用 `Path.home()` 或 `~/.hermes` 硬编码路径 → 使用 `/home/agentuser/.hermes/kanban.db`
2. **不要**把 frontmatter 里的 `status` 当作权威状态 → SQLite 才是
3. **不要**跳过 Git 提交 → Obsidian 没有自动保存到 Git
4. **不要**用 `agent_id` 查 assignee → 用 profile 名（如 `xingruyin`）
5. **不要**相信空的 kanban.db → 用 `find .../backlog/TSK-*.md` 核对文件系统
