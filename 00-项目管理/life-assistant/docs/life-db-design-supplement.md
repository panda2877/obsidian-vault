# 生活助手 M1 — 数据库设计补充文档（v0.8 原型改动）

> 作者：幸如音（技术专家）
> 日期：2026-05-10
> 项目：Hermes Dashboard — 生活助手模块
> 说明：本文档仅包含 v0.8 原型改动对应的补充内容，与主文档 `life-db-design.md` 配合使用。

---

## 1. 新增索引

### 1.1 todo_tasks — 复合索引 `idx_todo_priority_due`

为支持「紧急待办」模块的高效排序查询（按优先级 + 截止日期排序，取前3条），在 `todo_tasks` 表新增复合索引。

**查询场景**：

```sql
SELECT * FROM todo_tasks
WHERE status IN ('pending', 'in_progress')
ORDER BY
  CASE priority
    WHEN 'urgent' THEN 0
    WHEN 'high'   THEN 1
    WHEN 'medium' THEN 2
    WHEN 'low'    THEN 3
  END ASC,
  due_date ASC
LIMIT 3;
```

**索引定义**：

```sql
CREATE INDEX IF NOT EXISTS idx_todo_priority_due ON todo_tasks(priority, due_date);
```

**索引说明**：

| 属性 | 值 |
|------|-----|
| 索引名 | `idx_todo_priority_due` |
| 表名 | `todo_tasks` |
| 字段 | `priority, due_date` |
| 类型 | 普通 B-Tree 索引（非唯一） |
| 用途 | 加速紧急待办查询：按优先级排序 + 截止日期排序，配合 `LIMIT 3` 高效取顶 |

> ⚠️ **注意**：由于 `priority` 字段为文本类型（`'low'`, `'medium'`, `'high'`, `'urgent'`），SQLite 默认按字典序排序。实际查询中需配合 `CASE WHEN` 表达式将优先级映射为数值顺序，或确保应用层排序逻辑与索引前缀匹配。该索引主要加速 `WHERE status IN (...)` 过滤后的排序阶段。

---

## 2. 索引总览更新

将新增索引加入主文档的索引设计表中：

| 表名 | 索引名 | 字段 | 用途 |
|------|--------|------|------|
| `todo_tasks` | `idx_todo_priority_due` | `priority, due_date` | 加速紧急待办排序查询（v0.8 新增） |

---

## 3. 初始化函数更新

在 `lifeInitDb()` 函数中新增该索引的创建语句：

```javascript
async function lifeInitDb() {
  // ... 原有表创建和索引创建 ...

  // v0.8 新增：紧急待办复合索引
  db.run(`CREATE INDEX IF NOT EXISTS idx_todo_priority_due ON todo_tasks(priority, due_date);`)

  // ... 预设数据插入和持久化 ...
}
```