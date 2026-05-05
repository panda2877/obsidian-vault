# 看板速查

> **SQLite = 进度权威 | Obsidian = 任务详情**

---

## 新建任务

```
1. kanban_create(title, assignee, body, parents=[...])
2. 创建 Obsidian .md 文件（backlog/ 目录）
3. frontmatter: id, title, status=in_progress, priority, assignee, created
4. git add + commit + push
```

## 查询待办

```bash
python3 /home/agentuser/.hermes/skills/kanban-todo/scripts/kanban_todo.py
```

```python
# SQLite 快速计数
SELECT status, COUNT(*) FROM tasks WHERE id LIKE 'TSK-%' GROUP BY status
```

## 完成任务

```
1. UPDATE tasks SET status='done', completed_at=? WHERE id='{id}'
2. INSERT INTO checkpoints (id, task_id, phase, summary, agent_id, created_at)
3. 迁移文件 backlog/ → done/ + frontmatter status:done
4. git add + commit + push
```

## 查任务详情

```python
# Obsidian 文件
glob("/home/agentuser/obsidian-vault/00-项目管理/*/{backlog,done}/{id}.md")

# checkpoints 历史
SELECT phase, summary, blockers, next_steps, created_at
FROM checkpoints WHERE task_id='{id}' ORDER BY created_at
```

## 同步进度总览

```bash
python3 /home/agentuser/.hermes/skills/kanban-sync/scripts/sync.py
```

## 路径

| 资源 | 路径 |
|------|------|
| SQLite | `/home/agentuser/.hermes/kanban.db` |
| vault | `/home/agentuser/obsidian-vault/` |
| 任务卡 | `00-项目管理/{project}/{status}/TSK-{date}-{seq}.md` |
| 进度总览 | `00-项目管理/基于任务驱动的看板机制研究/.kanban/看板开发任务.md` |

## 禁止

- `Path.home()` / `~/.hermes` → 硬编码 `/home/agentuser/.hermes/kanban.db`
- frontmatter status 当权威 → SQLite 才是
- 不 git commit 直接 push
- assignee 用 `agent_id` → 用 profile 名（`xingruyin`）
- kanban.db 为空 → `find .../backlog/TSK-*.md` 核对文件系统

## skill 索引

| 场景 | skill |
|------|-------|
| 判断要不要建看板 + 分解任务 | `kanban-orchestrator` |
| 查待办列表 | `kanban-todo` |
| 完成任务标准流程 | `kanban-worker` |
| 同步 SQLite → Obsidian | `kanban-sync` |
