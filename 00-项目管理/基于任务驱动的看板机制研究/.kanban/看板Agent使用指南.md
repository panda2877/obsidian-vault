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
- 二者通过 `kanban-sync` 脚本同步

---

## 二、新建看板

### 2.1 整体看板总览文档模板

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

### 2.2 任务卡片模板

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

### 2.3 新建任务的标准流程

**Step 1：在 Obsidian 创建任务文件**

```bash
# 路径格式：{project}/backlog/TSK-{date}-{seq}.md
# seq 从 001 开始，按日期分组

TARGET_DIR="/home/agentuser/obsidian-vault/00-项目管理/{project}/backlog"
TASK_FILE="${TARGET_DIR}/TSK-$(date +%Y%m%d)-$(printf '%03d' $SEQ).md"
```

**Step 2：写入 frontmatter + 初始内容**

```markdown
---
id: TSK-20260505-001
title: {任务标题}
status: inbox
priority: P1
assignee: xingruyin
mission_id: {mission-id}
created: 2026-05-05T10:00:00+08:00
updated: 2026-05-05T10:00:00+08:00
---

## 任务目标

{具体目标描述}

## 检查点历史

（空，待 agent 运行时追加）

---

## 笔记

（待补充）
```

**Step 3：在 SQLite 中注册任务**

```python
import sqlite3
from datetime import datetime, timezone

conn = sqlite3.connect('/home/agentuser/.hermes/kanban.db')
cur = conn.cursor()
cur.execute("""
    INSERT INTO tasks (id, title, body, assignee, status, priority, created_by, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
""", (
    'TSK-20260505-001',
    '任务标题',
    '任务目标内容',
    'xingruyin',
    'backlog',       # inbox → backlog（Obsidian目录未开始=backlog）
    1,               # P1=1, P2=2, P3=3
    'xingruyin',
    int(datetime.now(timezone.utc).timestamp())
))
conn.commit()
conn.close()
```

**Step 4：Git 提交**

```bash
cd /home/agentuser/obsidian-vault
git add "00-项目管理/{project}/backlog/TSK-20260505-001.md"
git commit -m "feat(kanban): 新建任务 TSK-20260505-001"
git push
```

### 2.4 链接要求

| 链接类型 | 格式 | 示例 |
|---------|------|------|
| 任务卡片相互链接 | `[[backlog/TSK-20260504-001\|标题]]` | 任务目录页链接到具体卡片 |
| 主文档链接任务卡片 | `[[backlog/TSK-20260504-001\|[P0] 任务标题]]` | 看板总览链接到任务 |
| 跨文档交叉引用 | `[[看板开发任务#P0 — 核心闭环]]` | 方案文档引用看板章节 |

---

## 三、查询待办

**原则：进度统计以 SQLite 为准**

### 3.1 查全局进度（SQLite）

```python
import sqlite3
conn = sqlite3.connect('/home/agentuser/.hermes/kanban.db')
cur = conn.cursor()

# 按状态统计
cur.execute("""
    SELECT status, COUNT(*) as cnt
    FROM tasks
    WHERE id LIKE 'TSK-%'
    GROUP BY status
""")
for row in cur.fetchall():
    print(f"{row[0]}: {row[1]}")

# 按优先级统计 backlog
cur.execute("""
    SELECT priority, COUNT(*) as cnt
    FROM tasks
    WHERE status = 'backlog' AND id LIKE 'TSK-%'
    GROUP BY priority
    ORDER BY priority
""")
print("\nBacklog by priority:")
for row in cur.fetchall():
    print(f"  P{row[0]}: {row[1]}")

conn.close()
```

### 3.2 查某个任务的基本信息（SQLite）

```python
cur.execute("""
    SELECT t.id, t.title, t.status, t.assignee, t.priority,
           c.phase, c.summary, c.blockers, c.next_steps
    FROM tasks t
    LEFT JOIN checkpoints c ON t.id = c.task_id
    WHERE t.id = ?
""", ('TSK-20260505-001',))
row = cur.fetchone()
```

### 3.3 查所有 backlog 任务（文件优先，SQLite 计数）

```bash
# 文件系统：列出所有 backlog 任务
find /home/agentuser/obsidian-vault -path "*/backlog/TSK-*.md" | sort

# SQLite：快速计数（权威数字）
sqlite3 ~/.hermes/kanban.db "SELECT COUNT(*) FROM tasks WHERE status='backlog' AND id LIKE 'TSK-%'"
```

---

## 四、更新看板进度

### 4.1 完成任务（核心流程）

**原则：SQLite 更新状态 → Obsidian 文件迁移 → Git 提交**

**Step 1：更新 SQLite 状态**

```python
import sqlite3
from datetime import datetime, timezone

conn = sqlite3.connect('/home/agentuser/.hermes/kanban.db')
cur = conn.cursor()

task_id = 'TSK-20260505-001'

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

**Step 2：迁移 Obsidian 文件 + 更新 frontmatter**

```python
import shutil, re, os
from datetime import datetime, timezone

task_id = 'TSK-20260505-001'
project = '{project}'
vault = '/home/agentuser/obsidian-vault'
date_seq = task_id.split('-')  # ['TSK', '20260505', '001']

old_path = f"{vault}/00-项目管理/{project}/backlog/{task_id}.md"
new_path = f"{vault}/00-项目管理/{project}/done/{task_id}.md"

# 1. 迁移文件
os.makedirs(f"{vault}/00-项目管理/{project}/done", exist_ok=True)
shutil.move(old_path, new_path)

# 2. 更新 frontmatter
with open(new_path, 'r') as f:
    content = f.read()

content = re.sub(r'^status: .+$', 'status: done', content, flags=re.MULTILINE)
content = re.sub(r'^updated: .+$', f'updated: {datetime.now(timezone.utc).isoformat()}', content, flags=re.MULTILINE)

with open(new_path, 'w') as f:
    f.write(content)
```

**Step 3：Git 提交**

```bash
cd /home/agentuser/obsidian-vault
git add "00-项目管理/{project}/done/{task_id}.md"
git commit -m "done(kanban): 完成任务 {task_id}"
git push
```

### 4.2 更新进度总览文档

由 `kanban-sync` 脚本自动维护。如需手动更新看板开发任务.md：

```python
import re

doc_path = '/home/agentuser/obsidian-vault/00-项目管理/基于任务驱动的看板机制研究/看板开发任务.md'

with open(doc_path, 'r') as f:
    content = f.read()

# 重新计算合计行
total = done + backlog
pct = int(done / total * 100) if total > 0 else 0

# 替换合计行
old合计 = re.search(r'\|\*\*合计\*\*.*?\*\*', content, re.DOTALL).group()
new合计 = f"| **合计** | **{total}** | **{done}** | 0 | **{backlog}** | 0 | **{deprecated}** |"
content = content.replace(old合计, new合计)

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

**原则：任务详情看 Obsidian，状态变更操作 SQLite**

### 5.1 读任务卡片（Obsidian .md）

```python
def read_task_detail(task_id: str) -> str:
    """根据 task_id 找到对应的 .md 文件并返回内容"""
    import os, glob

    vault = '/home/agentuser/obsidian-vault'
    project_dirs = glob.glob(f"{vault}/00-项目管理/*/")

    for proj in project_dirs:
        for subdir in ['backlog', 'done', 'in-progress', 'review']:
            pattern = f"{proj}{subdir}/{task_id}.md"
            matches = glob.glob(pattern)
            if matches:
                with open(matches[0], 'r') as f:
                    return f.read()
    return None

# 示例
detail = read_task_detail('TSK-20260504-009')
print(detail)
```

### 5.2 从 Obsidian frontmatter 提取状态

```python
import re, frontmatter

def get_task_frontmatter(task_id: str) -> dict:
    path = find_task_file(task_id)  # 用上面 5.1 的方法
    post = frontmatter.load(path)
    return {
        'id': post['id'],
        'title': post['title'],
        'status': post['status'],
        'priority': post['priority'],
        'assignee': post['assignee'],
        'created': post['created'],
        'updated': post['updated'],
    }
```

### 5.3 从 checkpoints 了解任务历史（SQLite）

```python
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

| 操作 | 命令/方法 |
|------|----------|
| 新建任务 | 创建 .md + `INSERT INTO tasks` + git commit |
| 查看所有 backlog | `find .../backlog/TSK-*.md` 或 `SELECT COUNT(*) FROM tasks WHERE status='backlog'` |
| 查任务详情 | `read_task_detail(task_id)` → 读 Obsidian .md |
| 完成任务 | `UPDATE tasks SET status='done'` + 迁移文件 + git commit |
| 写 checkpoint | `INSERT INTO checkpoints` + 追加到 .md 的检查点历史章节 |
| 查整体进度 | `SELECT status, COUNT(*) FROM tasks GROUP BY status` |
| 同步到 Git | `cd /home/agentuser/obsidian-vault && git add -A && git commit -m "..." && git push` |

---

## 七、路径速查

| 资源 | 路径 |
|------|------|
| SQLite 数据库 | `/home/agentuser/.hermes/kanban.db` |
| Obsidian vault 根目录 | `/home/agentuser/obsidian-vault/` |
| 看板总览文档 | `00-项目管理/基于任务驱动的看板机制研究/.kanban/{project}-看板总览.md` |
| 任务卡片 | `00-项目管理/{project}/{status}/TSK-{date}-{seq}.md` |
| 任务模板 | `00-项目管理/{project}/templates/task-template.md` |
| kanban-sync 脚本 | `/home/agentuser/.hermes/skills/kanban-sync/scripts/sync.py` |

---

## 八、禁止事项

1. **不要**用 `Path.home()` 或 `~/.hermes` 硬编码路径 → 使用 `/home/agentuser/.hermes/kanban.db`
2. **不要**把 frontmatter 里的 `status` 当作权威状态 → SQLite 才是
3. **不要**跳过 Git 提交 → Obsidian 没有自动保存到 Git
4. **不要**相信空的 kanban.db → 用 `find .../backlog/TSK-*.md` 核对文件系统
