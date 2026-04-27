
### 设计理念

Auxiliary 是 Hermes 的副驾 LLM 路由中心。核心思路：让主模型专注复杂推理，让便宜/专用的副模型承担「脏活累活」，从而节省成本、提升效率。

### 支持配置的 8 个辅助任务

|   |   |
|---|---|
|**辅助模型**|**用途说明**|
|vision|截图 / 验证码 / 图片分析|
|web_extract|网页内容抓取与提炼|
|compression|上下文压缩摘要（节省 Token）|
|session_search|历史会话搜索与摘要|
|approval|高危命令审批决策|
|skills_hub|技能市场搜索与安装|
|mcp|MCP 服务调用辅助|
|flush_memories|记忆系统清理与重组|

### 配置示例

直接口头告知 Hermes：

代码语言：JavaScript

自动换行

AI代码解释

```
压缩会话的辅助模型帮我配置成 qwen3.5-plus
```

### 验证配置

代码语言：JavaScript

自动换行

AI代码解释

```
# 手动触发压缩
hermes compress

# 查看日志确认模型路由
tail -f ~/.hermes/logs/agent.log
```

日志中你应该看到类似：

代码语言：JavaScript

自动换行

AI代码解释

```
Auxiliary compression: using auto (qwen3.5-plus) at https://dashscope.aliyuncs.com/...
```

> **亮点三**：压缩阈值默认 50%，不同上下文长度的模型触发比例不同：1M 模型可分配最多 50K token 给摘要，200K 模型只有 10K。这比统一阈值更合理。
