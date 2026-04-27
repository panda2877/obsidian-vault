---
id: error-classification
tags: [concept, hermes, error-handling]
created: 2026-04-27
source: 01-学习/ai学习/Hermes Agent架构说明.md
---

# 错误分类与恢复机制

Hermes按错误分类各走各的恢复路径。

## ContextCompressor

压缩流程：裁旧工具输出 → 保护头部+尾部 → 中间用便宜模型摘要 → 增量更新。

触发阈值：context_length × 0.50

## ClassifiedError

14种FailoverReason，每个错误封装成只带四个布尔恢复标记：

- **retryable**：能不能直接重试
- **should_compress**：要不要先压缩上下文再重试
- **should_rotate_credential**：要不要切换到下一个API Key
- **should_fallback**：要不要切到fallback模型

主循环只看标记决定下一步，不自己做字符串匹配。

## 典型区分：429 vs 402

- **429限流**：临时，退避重试同一个Key就能恢复 → retryable=True
- **402额度耗尽**：账户钱扣光了，必须切Key → should_rotate_credential=True

不分清楚的话，Agent会在没钱的Key上反复退避到天荒地老。

## 用户中断处理

每轮开头检查_interrupt_requested。触发时：
- break出循环，持久化已有结果
- 补一个伪造的错误tool result，保证消息结构合法，下次恢复不被Provider拒
