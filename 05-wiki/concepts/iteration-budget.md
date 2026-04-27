---
id: iteration-budget
tags: [concept, hermes, mechanism]
created: 2026-04-27
source: 01-学习/ai学习/Hermes Agent架构说明.md
---

# 迭代预算机制

防止Agent在错误循环或幻觉里无限消耗token的硬上限机制。

## 规则

- 父Agent上限90轮，子Agent 50轮
- 每轮模型推理消耗1次迭代（不管这轮并行调了几个工具）
- 预算归零时强制退出主循环

## PTC Budget Refund

当本轮工具调用里只有execute_code时，刚扣掉的1次迭代会被退还。

**原理**：PTC已经用1轮模型推理打包了多次工具调用，系统再把这1轮也免掉。

**目的**：脚本密集型任务可能连写十几个脚本，预算很快被脚本执行吃掉。退还后预算全留给真正需要推理的轮次。
