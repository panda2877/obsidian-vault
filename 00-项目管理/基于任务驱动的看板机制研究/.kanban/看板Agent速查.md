# 看板速查

> **SQLite = 进度权威 | Obsidian = 任务详情**
> **模板和脚本已迁移至统一 skill 目录：`/home/agentuser/.hermes/skills/kanban/`**

---

## 操作索引

| 做什么 | 见章节 |
|--------|--------|
| 新建看板 + 任务 | `kanban` skill → references/kanban-agent-guide.md § 新建 |
| 认领任务 / 查待办 | `kanban-todo` skill |
| 完成任务（强制 sync.py） | `kanban` skill → references/kanban-agent-guide.md § 完成 |
| 查任务详情 | `kanban` skill → references/kanban-agent-guide.md § 详情 |
| 里程碑操作 | `kanban` skill → references/kanban-agent-guide.md § 里程碑操作 |
| 同步进度总览 | `kanban-sync` skill |
| 判断要不要建看板 | `kanban-orchestrator` skill |
| 高频踩坑 | `/home/agentuser/.hermes/skills/kanban/references/kanban-pitfalls.md` |

---

## § 新建

完整步骤见：`/home/agentuser/.hermes/skills/kanban/references/kanban-agent-guide.md`

**模板位置（不再在各项目目录下重复）：**
`/home/agentuser/.hermes/skills/kanban/templates/看板汇总模板.md`

---

## § 待办

```bash
python3 /home/agentuser/.hermes/skills/kanban/scripts/kanban_todo.py
```

---

## § 完成（强制跑 sync.py）

sync.py 是强制步骤，完整步骤见：`/home/agentuser/.hermes/skills/kanban/references/kanban-agent-guide.md`

```bash
python3 /home/agentuser/.hermes/skills/kanban/scripts/sync.py
```

---

## § 详情

```python
# Obsidian 文件
find /home/agentuser/obsidian-vault/00-项目管理 -name "{task_id}.md" 2>/dev/null

# checkpoints
SELECT phase, summary, blockers, next_steps, created_at
FROM checkpoints WHERE task_id='{id}' ORDER BY created_at

# 里程碑查询（新）
SELECT m.id, m.name, COUNT(t.id) AS task_count
FROM milestones m LEFT JOIN tasks t ON t.milestone_id = m.id
WHERE m.project_name = 'hermes多功能看板'
GROUP BY m.id ORDER BY m.sort_order;
```

---

## 路径速查

```
SQLite:   /home/agentuser/.hermes/kanban.db
vault:    /home/agentuser/obsidian-vault/00-项目管理/
skill:    /home/agentuser/.hermes/skills/kanban/
模板:     /home/agentuser/.hermes/skills/kanban/templates/看板汇总模板.md
脚本:     /home/agentuser/.hermes/skills/kanban/scripts/sync.py
速查:     /home/agentuser/.hermes/skills/kanban/references/kanban-agent-guide.md
```

---

## 禁止（高频踩坑）

| 禁止 | 正确做法 |
|------|----------|
| `Path.home()` / `~/.hermes` | 硬编码 `/home/agentuser/.hermes/kanban.db` |
| frontmatter status 当权威 | SQLite 才是 |
| 不 git commit 直接 push | 先 commit |
| assignee 用 agent_id | 用 profile 名（`xingruyin`）|
| kanban.db 为空时相信它 | `find .../backlog/TSK-*.md` 核对 |
| 用 `terminal` 写 SQLite | 用 `execute_code` |
