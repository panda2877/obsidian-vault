---
id: subagent-delegation
tags: [concept, hermes, delegation]
created: 2026-04-27
source: 01-学习/ai学习/Hermes Agent架构说明.md
---

# 子Agent委托机制

delegate_task工具fork新AIAgent处理复杂子任务。

## 核心机制

- 独立上下文，独立50轮预算
- 父子只通过任务描述（传入）和最终摘要（传出）通信
- 主Agent只看到委托调用本身和最终摘要，不看到中间过程

## 禁用5个工具

1. **delegate_task**：防套娃，Agent嵌套有开销
2. **clarify**：子Agent不能反问用户（用户不在场）
3. **memory**：子Agent不能写共享记忆，避免噪声污染
4. **send_message**：对外沟通只能经由父Agent
5. **execute_code**：子Agent定位是推理做事，不需要PTC折叠

## 硬约束

- 委托深度只有1层（父→子，子无法再委托）
- 并发上限3个
- 级联中断：父每30秒心跳，父中断后子连锁停下

## 应用场景

主Agent给科技/财经/国际各委托一个子Agent并行搜集新闻，主Agent只花1次迭代预算。
