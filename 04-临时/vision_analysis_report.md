# 银月视觉问题分析报告

## 问题1: "Invalid image source" 错误根因分析

### 错误来源

错误信息 `"Invalid image source"` 来自 `tools/vision_tools.py:492`:

```python
else:
    raise ValueError(
        "Invalid image source. Provide an HTTP/HTTPS URL or a valid local file path."
    )
```

这是在 `vision_analyze_tool()` 函数中，当图片 URL 既不是有效的 HTTP/HTTPS URL，也不是有效的本地文件路径时抛出的。

### MiniMax-M2.7 是否支持视觉？

**答案：MiniMax-M2.7 本身不支持视觉（图像识别）。**

证据：

1. **`_API_KEY_PROVIDER_AUX_MODELS`** (auxiliary_client.py:137):
   ```python
   "minimax": "MiniMax-M2.7",  # MiniMax 用于文本辅助任务，不是视觉
   ```

2. **`_PROVIDER_VISION_MODELS`** (auxiliary_client.py:148):
   ```python
   _PROVIDER_VISION_MODELS: Dict[str, str] = {
       "xiaomi": "mimo-v2-omni",
       "zai": "glm-5v-turbo",
   }
   ```
   **MiniMax 不在这个列表中** — 没有任何视觉模型映射。

3. **`_VISION_AUTO_PROVIDER_ORDER`** (auxiliary_client.py:1852):
   ```python
   _VISION_AUTO_PROVIDER_ORDER = (
       "openrouter",   # 第一个候选：需要 OPENROUTER_API_KEY
       "nous",          # 第二个候选：需要 Nous Portal OAuth
   )
   ```
   MiniMax **不在**视觉自动检测链中。

### 为什么 vision_analyze 会报 "Invalid image source"？

这是 **URL 验证失败**，不是 API 调用失败。流程如下：

1. 用户发送图片 URL → `vision_analyze_tool()` 被调用
2. 函数检查 URL 格式：
   - 如果是 HTTP/HTTPS URL，调用 `_validate_image_url()` → 调用 `is_safe_url()`（SSRF 检查）
   - 如果是本地文件，调用 `local_path.is_file()`
3. **URL 验证失败** → 抛出 "Invalid image source"

但是，**为什么 URL 验证会失败？** 最可能的原因是：

1. **传入的 URL 包含特殊字符或格式问题** — 例如中文路径、特殊协议头
2. **URL 被错误解析** — 例如 `urlparse()` 失败
3. **SSRF 安全检查拒绝** — `is_safe_url()` 返回 False

### OpenClaw 为什么能工作？

OpenClaw 是一个独立的开源项目（https://github.com/openclaw/openclaw），它：
- 使用自己的视觉处理逻辑
- 可能内置了对 MiniMax 视觉 API 的直接调用（MiniMax 确实有视觉 API，但 M2.7 模型本身不支持）
- 或者 OpenClaw 配置了不同的视觉后端（如 Claude/ GPT-4V）

**关键点**：OpenClaw 能识别图片 ≠ MiniMax-M2.7 能识别图片。OpenClaw 可能配置了其他视觉模型。

---

## 问题2: 是否需要新增专门的视觉妹妹？

### 当前架构分析

Hermes 的视觉处理架构：

```
vision_analyze tool
    ↓
async_call_llm(task="vision")
    ↓
resolve_vision_provider_client()
    ↓
检查顺序：
  1. 用户主 provider（如配置了 OpenRouter/Nous） 
  2. OpenRouter (Gemini Flash)
  3. Nous Portal
```

### 当前配置问题

根据 `.env` 文件：
- **没有** `OPENROUTER_API_KEY`
- **没有** `GOOGLE_API_KEY` / `GEMINI_API_KEY`  
- **没有** Nous Portal OAuth 配置
- **没有** 其他视觉 API key

这意味着 **`resolve_vision_provider_client()` 无法解析任何视觉后端**，返回 `client is None`。

### 解决方案

**方案 A（推荐）：配置视觉后端 API Key**

在 `config.yaml` 中添加或让用户设置：
```yaml
auxiliary:
  vision:
    provider: "openrouter"  # 或 "gemini"
    model: "google/gemini-3-flash-preview"
```

或设置环境变量：
```bash
OPENROUTER_API_KEY=sk-xxx
# 或
GEMINI_API_KEY=xxx
```

**方案 B：新增专门的视觉妹妹**

如果希望保持架构清晰，可以新增一个专门处理视觉的子 agent：

1. 给她配置支持视觉的 API（如 Claude、GPT-4V、Gemini）
2. 通过 `delegate_task` 工具将视觉任务委托给她
3. 优点：视觉能力独立、维护简单
4. 缺点：增加延迟（额外 API 调用）

**方案 C：修改 MiniMax 配置使用视觉 API**

MiniMax 实际上有视觉 API（通过 MiniMax 自己的接口），但需要：
- 配置 `auxiliary.vision.provider: "minimax"`
- 配置 `auxiliary.vision.model` 为支持视觉的模型
- 这需要 MiniMax 账户有视觉模型的访问权限

---

## 建议

1. **首先排查 "Invalid image source" 的真正原因**
   - 查看完整错误日志
   - 确认传入的图片 URL 格式
   
2. **如果问题是「没有视觉 API key」**
   - 最简单的修复：配置 `OPENROUTER_API_KEY` 或 `GEMINI_API_KEY`
   - Hermes 的视觉工具默认使用 Gemini Flash（免费 tier 可用）

3. **如果确定需要新增视觉妹妹**
   - 建议给她配置 Gemini/Claude 等支持视觉的模型
   - 通过 `delegate_task` 与主 agent 协作

4. **关于 OpenClaw**
   - OpenClaw 能用 ≠ MiniMax-M2.7 支持视觉
   - OpenClaw 可能内置了额外的视觉处理或配置了其他视觉模型
   - 需要具体查看 OpenClaw 的配置来确定它使用的视觉后端

---

## 参考：Hermes 视觉工具架构

```
vision_analyze_tool()
├── _validate_image_url() → is_safe_url()  [SSRF 检查]
├── _download_image()  [如果 URL 是远程图片]
├── _image_to_base64_data_url()  [转换为 base64]
├── async_call_llm(task="vision", messages=[...])
│   ├── resolve_vision_provider_client()
│   │   ├── 1. 主 provider（如配置了） 
│   │   ├── 2. OpenRouter (google/gemini-3-flash-preview)
│   │   └── 3. Nous Portal (gemini-3-flash)
│   └── [调用视觉 LLM API]
└── extract_content_or_reasoning(response)
```
