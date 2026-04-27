---
id: system-prompt-engineering
tags: [concept, hermes, prompt]
created: 2026-04-27
source: 01-学习/ai学习/Hermes Agent架构说明.md
---

# 系统提示词工程

模型推理前系统提示词的8层拼接顺序。

## 拼接顺序（越稳定越靠前）

1. **身份**：默认"You are Hermes Agent..."，SOUL.md可替换
2. **工具行为引导**：根据模型家族注入不同内容
3. **外部系统提示**：网关层/API/用户配置的补充指令
4. **记忆**：MEMORY.md + USER.md + 外部Provider回忆内容
5. **技能索引**：紧凑目录（标签包起来），按需加载
6. **项目上下文**：.hermes.md/AGENTS.md等指令文件
7. **运行时元数据**：时间、WSL/Termux、平台格式约定

## 模型特定引导

**GPT/Gemini/Grok**：额外注入TOOL_USE_ENFORCEMENT_GUIDANCE，"说做就做，别光说不动"

**GPT专属**：应对GPT老毛病的各模块（部分结果放弃/跳过前置检查/不调工具编答案/没验证说完成）

**Claude**：不需要额外引导，不同模型工具调用行为有差异

## 安全扫描

项目上下文注入前过10条正则，检测prompt injection/隐蔽HTML注入/数据外泄等。

**盲区**：只覆盖英文模式，中文prompt injection不在检测范围内。

## 前缀缓存

越稳定的内容越靠前，配合前缀缓存，只有尾巴变化时缓存命中率高。

## 相关链接

  - [[AIAgent主循环]]
  - [[中文PromptInjection检测盲区]]
  - [[记忆系统]]
