# 看板速查

> **SQLite = 进度权威 | Obsidian = 任务详情**

---

## 操作索引

| 做什么 | 见章节 |
|--------|--------|
| 新建任务 | § 新建 |
| 认领任务 / 查待办 | § 待办 |
| 完成任务 | § 完成 |
| 查任务详情 | § 详情 |
| 同步进度总览 | § 同步 |
| 判断要不要建看板 | § 编排 |

---

## § 新建

```bash
# 1. kanban_create → SQLite
# 2. 创建 .md 文件（backlog/）
# 3. 创建项目汇总 .md 文件（见下方命名规范）
# 4. git add + commit + push
```

frontmatter 必须字段：`id`, `title`, `status`, `priority`, `assignee`, `created`, `updated`

### 汇总文件规范

**必须创建项目汇总文件**，命名规则：`{项目名称}.md`，放在项目根目录。

内容模板：
```markdown
# {项目名称}

> 状态：新建 | 创建：{日期}

---

## 进度总览

| 阶段 | 总数 | Done | In Progress | Backlog | Blocked |
|------|------|------|-------------|---------|---------|

---

## 任务总览

（每个任务一行：标题 + status badge + 负责人 + [[链接|详情]]）

---

## 任务卡片目录

### {阶段名称}

| ID | 标题 | 负责人 | 状态 | 说明 |
|----|------|--------|------|------|
| TSK-... | [[backlog/TSK-...\|标题]] | 负责人 | 📋 backlog | 说明 |

（按阶段分节，每节一个表格）

---

## 里程碑

| # | 阶段 | 负责人 | 任务 |
|---|------|--------|------|
```

**禁止**：汇总文件命名用"看板开发任务"等通用名 → 必须用项目名称

---

## § 待办

```bash
python3 /home/agentuser/.hermes/skills/kanban-todo/scripts/kanban_todo.py
```

```sql
SELECT status, COUNT(*) FROM tasks WHERE id LIKE 'TSK-%' GROUP BY status
```

---

## § 完成

```sql
-- 1. 更新 SQLite
UPDATE tasks SET status='done', completed_at=? WHERE id='{id}';
INSERT INTO checkpoints (id, task_id, phase, summary, agent_id, created_at)
  VALUES ('{id}-f', '{id}', 'done', '完成', 'xingruyin', '{iso}');

-- 2. 迁移文件 backlog/ → done/，frontmatter status: done

-- 3. git add + commit + push
```

---

## § 详情

```python
# Obsidian 文件
glob("/home/agentuser/obsidian-vault/00-项目管理/*/{backlog,done}/{id}.md")

# checkpoints
SELECT phase, summary, blockers, next_steps, created_at
FROM checkpoints WHERE task_id='{id}' ORDER BY created_at
```

---

## § 同步

```bash
python3 /home/agentuser/.hermes/skills/kanban-sync/scripts/sync.py
```

---

## § 编排

加载 `kanban-orchestrator` skill。判断是否建看板：
- 多角色协作 / 持久化 / 需人工介入 / 需并行 / 需 review / 审计追踪 → 建看板
- 否则 → `delegate_task` 或直接执行

---

## 路径

```
SQLite:   /home/agentuser/.hermes/kanban.db
vault:    /home/agentuser/obsidian-vault/
任务卡:   00-项目管理/{project}/{status}/TSK-{date}-{seq}.md
进度总览: .kanban/看板开发任务.md
速查:     .kanban/看板Agent速查.md
```

---

## 禁止（高频踩坑）

```
✗ Path.home() / ~/.hermes       → /home/agentuser/.hermes/kanban.db
✗ frontmatter status 当权威      → SQLite 才是
✗ 不 git commit 直接 push
✗ assignee 用 agent_id          → 用 profile 名（xingruyin）
✗ kanban.db 为空时相信它         → find .../backlog/TSK-*.md 核对
```

---

## skill 速查

| 场景 | skill |
|------|-------|
| 判断要不要建 + 分解 | `kanban-orchestrator` |
| 查待办列表 | `kanban-todo` |
| 完成任务 | `kanban-worker` |
| 同步 SQLite→Obsidian | `kanban-sync` |
