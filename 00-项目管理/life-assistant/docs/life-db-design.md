# 生活助手 M1 — 数据库设计文档

> 作者：幸如音（技术专家）
> 日期：2026-05-10
> 项目：Hermes Dashboard — 生活助手模块

---

## 1. 概述

生活助手模块使用与看板**共用的 SQLite 数据库**（`kanban.db`），通过 `sql.js`（WASM 驱动）在内存中操作并持久化到磁盘。

- **数据库文件**：`/home/agentuser/.hermes/kanban.db`（由 `config.sqlite.dbPath` 配置）
- **驱动**：`sql.js` v1.11+（纯 JS SQLite，无需本地编译）
- **持久化机制**：每次写操作后调用 `sqlite.saveDb()` 将内存数据写回磁盘文件
- **表前缀**：无需前缀，所有生活助手表独立命名，与看板 `tasks` 表共存

---

## 2. 完整 CREATE TABLE 语句

### 2.1 device_bindings — 设备绑定表

记录已授权的手机设备，实现"一次绑定，自动登录"。

```sql
CREATE TABLE IF NOT EXISTS device_bindings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    token_hash  TEXT    NOT NULL,                -- LIFE_TOKEN 的 SHA-256 哈希
    device_id   TEXT    NOT NULL UNIQUE,          -- 设备唯一标识（前端生成 UUID）
    device_name TEXT    NOT NULL DEFAULT '',      -- 设备名称（如 "iPhone 15 Pro"）
    last_login_at TEXT  NOT NULL DEFAULT (datetime('now')),  -- 最后登录时间
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),  -- 绑定时间
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))   -- 更新时间
);
```

**约束说明**：
- `device_id` UNIQUE：同一设备只能绑定一次
- `token_hash` 存储哈希而非明文，防止 Token 泄露
- 所有时间字段使用 ISO 8601 格式文本（SQLite 无原生 DATETIME 类型）

### 2.2 finance_categories — 记账分类表

预设 + 用户自定义的收支分类。

```sql
CREATE TABLE IF NOT EXISTS finance_categories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,                -- 分类名称（如 "餐饮"、"工资"）
    type        TEXT    NOT NULL CHECK(type IN ('income', 'expense')),  -- 类型：收入/支出
    icon        TEXT    NOT NULL DEFAULT '📦',   -- Emoji 图标
    sort_order  INTEGER NOT NULL DEFAULT 0,      -- 排序序号（越小越靠前）
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- 唯一约束：同一类型下分类名称不可重复
CREATE UNIQUE INDEX IF NOT EXISTS idx_cat_name_type ON finance_categories(name, type);
```

### 2.3 finance_records — 记账记录表

每一笔收支明细。

```sql
CREATE TABLE IF NOT EXISTS finance_records (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    type        TEXT    NOT NULL CHECK(type IN ('income', 'expense')),  -- 收支类型
    amount      REAL    NOT NULL CHECK(amount > 0),   -- 金额（正数）
    category_id INTEGER NOT NULL,                     -- 分类 ID → finance_categories.id
    note        TEXT    NOT NULL DEFAULT '',           -- 备注
    record_date TEXT    NOT NULL DEFAULT (date('now')), -- 记账日期（YYYY-MM-DD）
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (category_id) REFERENCES finance_categories(id)
);
```

### 2.4 todo_tasks — 待办任务表

个人待办事项。

```sql
CREATE TABLE IF NOT EXISTS todo_tasks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT    NOT NULL,                    -- 任务标题
    description TEXT    NOT NULL DEFAULT '',          -- 详细描述
    category    TEXT    NOT NULL DEFAULT 'general',   -- 分类标签（如 general, shopping, health）
    priority    TEXT    NOT NULL DEFAULT 'medium' CHECK(priority IN ('low', 'medium', 'high', 'urgent')),
    status      TEXT    NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'in_progress', 'done', 'cancelled')),
    due_date    TEXT    DEFAULT NULL,                 -- 截止日期（YYYY-MM-DD，可选）
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);
```

---

## 3. 索引设计

| 表名 | 索引名 | 字段 | 用途 |
|------|--------|------|------|
| `device_bindings` | `idx_device_token_hash` | `token_hash` | 快速查询 Token 对应的绑定设备 |
| `device_bindings` | `idx_device_id` | `device_id` (UNIQUE) | 设备去重（已由 UNIQUE 约束自动创建） |
| `finance_records` | `idx_finance_date` | `record_date` | 按日期范围查询账单 |
| `finance_records` | `idx_finance_type_date` | `type, record_date` | 按类型+日期组合查询 |
| `finance_records` | `idx_finance_category` | `category_id` | 按分类统计 |
| `finance_categories` | `idx_cat_name_type` | `name, type` (UNIQUE) | 分类名称去重 |
| `todo_tasks` | `idx_todo_status` | `status` | 按状态筛选待办 |
| `todo_tasks` | `idx_todo_due` | `due_date` | 按截止日期排序 |
| `todo_tasks` | `idx_todo_priority` | `priority` | 按优先级排序 |

```sql
-- 完整索引创建语句
CREATE INDEX IF NOT EXISTS idx_device_token_hash ON device_bindings(token_hash);

CREATE INDEX IF NOT EXISTS idx_finance_date ON finance_records(record_date);
CREATE INDEX IF NOT EXISTS idx_finance_type_date ON finance_records(type, record_date);
CREATE INDEX IF NOT EXISTS idx_finance_category ON finance_records(category_id);

CREATE INDEX IF NOT EXISTS idx_todo_status ON todo_tasks(status);
CREATE INDEX IF NOT EXISTS idx_todo_due ON todo_tasks(due_date);
CREATE INDEX IF NOT EXISTS idx_todo_priority ON todo_tasks(priority);
```

---

## 4. 初始化数据（系统预设分类）

在首次启动时，通过 `lifeInitDb()` 函数自动插入以下预设分类：

### 4.1 支出分类（expense）

| name | icon | sort_order |
|------|------|-----------|
| 餐饮 | 🍜 | 1 |
| 交通 | 🚗 | 2 |
| 购物 | 🛒 | 3 |
| 住房 | 🏠 | 4 |
| 娱乐 | 🎮 | 5 |
| 医疗 | 💊 | 6 |
| 教育 | 📚 | 7 |
| 通讯 | 📱 | 8 |
| 服饰 | 👔 | 9 |
| 其他支出 | 📦 | 99 |

### 4.2 收入分类（income）

| name | icon | sort_order |
|------|------|-----------|
| 工资 | 💰 | 1 |
| 奖金 | 🏆 | 2 |
| 兼职 | 💼 | 3 |
| 理财 | 📈 | 4 |
| 红包 | 🧧 | 5 |
| 其他收入 | 📦 | 99 |

### 4.3 初始化 SQL

```sql
-- 支出分类
INSERT OR IGNORE INTO finance_categories (name, type, icon, sort_order) VALUES
('餐饮', 'expense', '🍜', 1),
('交通', 'expense', '🚗', 2),
('购物', 'expense', '🛒', 3),
('住房', 'expense', '🏠', 4),
('娱乐', 'expense', '🎮', 5),
('医疗', 'expense', '💊', 6),
('教育', 'expense', '📚', 7),
('通讯', 'expense', '📱', 8),
('服饰', 'expense', '👔', 9),
('其他支出', 'expense', '📦', 99);

-- 收入分类
INSERT OR IGNORE INTO finance_categories (name, type, icon, sort_order) VALUES
('工资', 'income', '💰', 1),
('奖金', 'income', '🏆', 2),
('兼职', 'income', '💼', 3),
('理财', 'income', '📈', 4),
('红包', 'income', '🧧', 5),
('其他收入', 'income', '📦', 99);
```

---

## 5. 数据库初始化函数设计

在 `backend/services/lifeDb.js` 中实现 `lifeInitDb()` 函数：

```javascript
/**
 * 初始化生活助手数据库表结构 + 预设数据
 * 在 server.js 启动时调用
 */
async function lifeInitDb() {
  // 1. 创建 4 张表（CREATE TABLE IF NOT EXISTS）
  // 2. 创建所有索引（CREATE INDEX IF NOT EXISTS）
  // 3. 插入预设分类（INSERT OR IGNORE）
  // 4. 调用 sqlite.saveDb() 持久化
}
```

---

## 6. 与看板数据的关系

| 方面 | 看板（tasks） | 生活助手 |
|------|-------------|---------|
| 数据库 | 同一 `kanban.db` | 同一 `kanban.db` |
| 表名 | `tasks` | `device_bindings`, `finance_records`, `finance_categories`, `todo_tasks` |
| 数据关联 | 无直接外键关联 | 表间通过 `category_id` 外键关联 |
| 初始化时机 | 由 Hermes CLI 写入 | 由 BFF 启动时 `lifeInitDb()` 自动初始化 |

> ⚠️ **注意**：`sql.js` 是 WASM 内存数据库，每次写操作后必须调用 `saveDb()` 持久化到磁盘。如果 BFF 重启前未保存，数据会丢失。