---
id: context-compression
tags: [concept, hermes, context]
created: 2026-04-27
source: 01-学习/ai学习/Hermes Agent架构说明.md
---

# 上下文压缩

上下文超限时用有损压缩续命，但历史不丢。

## 压缩流程

1. **裁旧工具输出**（不调LLM）：替换为"[Old tool output cleared]"。通常这一步就够。
2. **保护头部**：系统提示词 + 前3条消息不动。
3. **保护尾部**：最近完整对话不动，预算=context_length×0.50×0.20
4. **中间摘要**：用便宜模型做摘要，拼SUMMARY_PREFIX"这是来自前一个上下文窗口的交接"。
5. **增量更新**：二次压缩在已有摘要上更新，摘要上限12000 token。

## Session链保历史

压缩时：
1. 结束当前session，原始对话完整保留在SQLite
2. 开新session，压缩摘要作为新session起点
3. parent_session_id指回旧session ID

结果：模型层看到压缩版，数据库层存完整版，两个目标分开满足。

## 关键区别

- session_search能搜到历史 ≠ Agent记住了
- session_search是按需检索，结果只是当次推理的临时上下文
- 真正持久的记忆只有一条路：模型主动调memory工具写入MEMORY.md
