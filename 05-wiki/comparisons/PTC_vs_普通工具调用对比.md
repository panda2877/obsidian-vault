---
id: ptc-vs-normal-toolcall
tags: [comparison, hermes, ptc]
created: 2026-04-27
source: 01-学习/ai学习/Hermes Agent架构说明.md
---

# PTC vs 普通工具调用

## 普通工具调用

模型调web_search → 拿结果 → 再推理下一步 → 调read_file → 拿结果 → 再推理...

**8次工具调用 = 8轮模型推理 = 吃掉8次迭代预算**

## PTC (Programmatic Tool Calling)

模型一轮里写出一整段Python脚本，脚本内部通过RPC把web_search/read_file/write_file串起来跑。

**8次工具调用 = 1轮模型推理 = 1次迭代预算**

PTC再退1次，所以执行PTC的预算成本 = 0。

## 对比效果

| 方式 | 工具执行8次 | 模型推理轮次 | 迭代预算消耗 |
|------|------------|-------------|-------------|
| 普通调用 | 8次 | 8轮 | 8次 |
| PTC | 8次 | 1轮 | 0次（退1） |

PTC把多次工具调用折叠成1轮推理，大幅节省迭代预算和API调用成本。

## 相关链接

  - [[迭代预算机制]]
  - [[AIAgent主循环]]
