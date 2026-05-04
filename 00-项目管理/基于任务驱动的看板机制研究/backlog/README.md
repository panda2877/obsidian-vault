# Backlog

所有待开发任务卡片，按优先级分组。点击卡片标题可跳转至详细页面。

## 进度总览

> 📋 总计：**12** 任务 | ✅ Done: 1 | 🔄 In Progress: 1 | 📋 Backlog: 7 | 🔴 Blocked: 1 | ❌ Obsolete: 3

---

## P0 — 核心闭环

| ID | 标题 | 状态 | 说明 |
|----|------|------|------|
| TSK-20260504-001 | [[TSK-20260504-001\|[P0] Hook 集成：on_task_start]] | ✅ done | 已完成 |
| TSK-20260504-002 | [[TSK-20260504-002\|[P0] Hook 集成：on_phase_change]] | 🔄 reassessed | 方案变更：不再需要独立 phase_change 事件 |
| TSK-20260504-003 | [[TSK-20260504-003\|[P0] Hook 集成：on_task_done]] | 🔄 in_progress | DB 目标改为原生 kanban.db |
| TSK-20260504-012 | [[TSK-20260504-012\|[P0] 快照写入机制研究]] | ❌ obsolete | 整合方案已定义字段，无需单独研究 |

---

## P1 — 原生嫁接改造

| ID | 标题 | 状态 | 说明 |
|----|------|------|------|
| TSK-20260504-004 | [[TSK-20260504-004\|[P1] 迁移到原生 kanban.db]] | 🔴 blocked | 依赖修改迁移函数 |
| TSK-20260504-005 | [[TSK-20260504-005\|[P1] FastAPI 后端：任务 CRUD + Checkpoint API]] | ❌ obsolete | 原生已有 CLI + tools |
| TSK-20260504-006 | [[TSK-20260504-006\|[P2] React 前端：看板界面]] | ❌ obsolete | 原生已有 dashboard |
| TSK-20260504-007 | [[TSK-20260504-007\|[P1] Obsidian 同步层改造]] | 📋 backlog | 改为调用原生 kanban_db 层 |
| TSK-20260504-008 | [[TSK-20260504-008\|[P1] Agent 注册表改造]] | 📋 backlog | 复用原生 agent_registry 表 |

---

## P2 — 能力增强

| ID | 标题 | 状态 | 说明 |
|----|------|------|------|
| TSK-20260504-009 | [[TSK-20260504-009\|[P2] Review Gate：人工审批通知]] | 📋 backlog | 简化为原生 blocked + comment |
| TSK-20260504-010 | [[TSK-20260504-010\|[P2] 实时推送：WebSocket 任务状态同步]] | ❌ obsolete | 原生已有 kanban_notify_subs |
| TSK-20260504-011 | [[TSK-20260504-011\|[P2] cron 看门狗：超时任务检测]] | 📋 backlog | 复用原生 claim TTL 机制 |
