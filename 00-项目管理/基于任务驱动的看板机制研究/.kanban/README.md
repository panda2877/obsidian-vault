# 看板元数据

本目录存放看板机制的配置和数据库文件。

## 文件说明

| 文件 | 说明 |
|------|------|
| `README.md` | 本文件 |

## 数据库

SQLite 数据库位于：

```
~/.hermes/memory/checkpoints.db   # Checkpoints 表
~/.hermes/memory/tasks.db         # Tasks 表（待建）
```

## 看板列说明

| 列 | 说明 |
|----|------|
| backlog | 未开始，尚未认领 |
| in_progress | 进行中，agent 正在处理 |
| review | 待审查，等待人工审批 |
| done | 已完成 |

## 优先级说明

| 优先级 | 说明 |
|--------|------|
| P0 | Urgent，需立即处理 |
| P1 | High，需尽快处理 |
| P2 | Normal，标准优先级 |
| P3 | Low，较低优先级 |
