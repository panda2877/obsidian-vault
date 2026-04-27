---
id: aiagent-main-loop
tags: [entity, hermes, core]
created: 2026-04-27
source: 01-学习/ai学习/Hermes Agent架构说明.md
---

# AIAgent 主循环

Hermes的核心执行引擎，整个项目的心脏。

## 主循环骨架

while iteration_budget.remaining > 0:
    response = client.chat.completions.create(model=model, messages=messages, tools=tool_schemas, stream=True)
    if response 有 tool_calls:
        执行工具（可能并行）
        iteration_budget.consume()
    else:
        return response.content

## 三种退出路径

1. **正常返回**：模型给最终文本，无tool_calls
2. **预算耗尽**：iteration_budget.remaining 归零，硬上限
3. **用户中断**：_interrupt_requested 被置位，break出循环

## 迭代预算机制

- 父Agent上限90轮，子Agent 50轮
- 每轮模型推理消耗1次迭代（不管并行调了几个工具）
- **PTC refund**：本轮只有execute_code时，扣掉的1次被退还
  - PTC已经用1轮模型推理打包了多次工具调用，系统再免1轮
  - 目的：让脚本执行零成本，预算全留给推理轮次

## 工具并行执行

三个集合决定能否并行：
- **_NEVER_PARALLEL_TOOLS**：`clarify`（会跟用户交互）
- **_PARALLEL_SAFE_TOOLS**：只读工具（read_file/search_files/vision_analyze等）
- **_PATH_SCOPED_TOOLS**：`read_file/write_file/patch`（路径不重叠才能并行）

路径冲突判定：同一路径 或 父子路径（如/./a和/./a/b.txt）→ 必须串行

## 子Agent委托（delegate_task）

- fork新AIAgent，独立上下文，独立50轮预算
- 父子只通过任务描述（传入）和最终摘要（传出）通信
- **禁用5个工具**：delegate_task/clarify/memory/send_message/execute_code
- **硬约束**：深度只有1层，并发上限3个
- **级联中断**：父每30秒心跳，子Agent在父中断后连锁停下
