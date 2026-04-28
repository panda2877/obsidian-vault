# WeChat 发文件 Bug 修复任务总结

**执行时间：** 2026-04-26
**执行人：** 子曰（subagent）
**接收人：** 银月

---

## 一、任务执行情况总结

### 1.1 问题描述

**现象：** WeChat 发文件时，系统报错 `FileNotFoundError`，但文件实际存在且路径格式正确。

**影响：** 用户无法通过 `MEDIA:` 标签发送文件，导致业务流程阻塞。

### 1.2 排查过程

| 轮次 | 排查方向 | 发现 | 结论 |
|------|----------|------|------|
| 第一轮 | asyncio.timeout() 超时 | 怀疑超时导致异常 | ❌ 实际不是 |
| 第二轮 | gateway 日志 + nginx 404 | 发现路径被替换成错误文本 | ⚠️ 定位到 MEDIA: 解析异常 |
| 第三轮 | base.py 的 extract_media 函数 | 正则 `\S+` 匹配了任意文本 | ✅ 找到根因 |
| 第四轮 | token 和 Bot 状态 | token 未过期，Bot 正常在线 | ✅ 排除账号问题 |

**排查链路：**
```
用户发送 MEDIA:/path/to/file
    ↓
extract_media() 正则匹配
    ↓
\S+ 匹配到"路径格式也正确"（消息文本）
    ↓
误当成文件路径 → FileNotFoundError
    ↓
nginx 404（文件不存在）
```

### 1.3 根因分析

**根因位置：** `base.py` 中的 `extract_media()` 函数

**问题代码：**
```python
# 原正则（有问题）
MEDIA_PATTERN = r"MEDIA:(\S+)"
```

**问题原因：** `\S+` 匹配任意非空白字符，包括：
- 中文文本（如"路径格式也正确"）
- URL（如 http://...）
- 任意字符串

导致消息文本被误识别为文件路径。

### 1.4 修复方案

**三层防护：**

1. **正则收紧：** 去掉 `\S+` 兜底匹配，只匹配合法的 Unix 文件路径格式
   ```python
   # 新正则
   MEDIA_PATTERN = r"MEDIA:((?:/[^/\s]+)+|~/[^\s]+)"
   ```

2. **前缀检查：** 路径必须以 `/` 或 `~/` 开头
   ```python
   if not (path.startswith('/') or path.startswith('~/')):
       return None
   ```

3. **文件存在性验证：** `os.path.isfile()` 验证文件真实存在
   ```python
   if not os.path.isfile(full_path):
       return None
   ```

### 1.5 测试验证

| 测试用例 | 输入 | 期望结果 | 实际结果 |
|----------|------|----------|----------|
| 中文文本 | `MEDIA:路径格式也正确` | 不匹配 | ✅ |
| 普通文本 | `MEDIA:hello_world` | 不匹配 | ✅ |
| URL | `MEDIA:http://example.com` | 不匹配 | ✅ |
| 真实文件 | `MEDIA:/home/user/需求文档.pdf` | 正确提取 | ✅ |

**最终结果：** 文件发送成功，宝子收到了需求文档 ✅

---

## 二、自我复盘

### 2.1 排查过程有没有走弯路？

**有。** 第一轮排查方向错了，怀疑了 asyncio.timeout()，浪费了时间。

**教训：** 应该先看完整的错误堆栈和日志，确认是哪个函数抛出的异常，而不是凭感觉猜测。

### 2.2 信息记录是否完整？

**不够完整。** 排查过程中发现的一些中间状态（如 gateway 日志片段、nginx 404 的具体 URL）没有完整记录下来，导致需要回头重新查。

**改进：** 排查过程中发现的关键日志应该即时复制保存。

### 2.3 和银月的沟通有没有可以优化的地方？

**有。** 第一次汇报时没有给足够的上下文，导致银月需要反复追问。

**改进：** 汇报时先说结论，再给细节，格式参考：本轮排查发现 → 关键证据 → 下一步行动。

### 2.4 时间/效率方面有没有可以改进的地方？

**可以。** 这次排查花了 4 轮，主要是因为：
1. 第一轮走错方向
2. 没有先看日志就下结论

**改进：** 遇到问题时，优先查看完整日志/堆栈，再基于证据推理。

---

## 三、「发送文件」执行方案

### 3.1 WeChat 文件发送完整流程

```
用户发送消息（含 MEDIA: 标签）
    ↓
base.py receive_message()
    ↓
extract_media() 提取路径
    ↓
检查路径前缀（/ 或 ~/）
    ↓
os.path.isfile() 验证文件存在
    ↓
调用文件发送 API
    ↓
返回发送结果
```

### 3.2 正常情况下如何发送文件

**命令格式：**
```
MEDIA:/absolute/path/to/file.pdf
```

或：

```
MEDIA:~/relative/path/to/file.pdf
```

**路径格式要求：**
- 必须是以 `/` 开头的绝对路径，或 `~/` 开头的相对路径
- 不能包含空格
- 文件必须真实存在
- 文件名不能包含非 ASCII 字符（如果有，请先重命名）

### 3.3 遇到问题时的排查思路

**Step 1：看错误类型**
- `FileNotFoundError` → 文件不存在或路径解析错误
- `PermissionError` → 权限不足
- `asyncio.TimeoutError` → 超时，可能是网络或账号问题

**Step 2：查日志**
```bash
# 查看最近 gateway 日志
tail -n 100 /var/log/gateway.log | grep ERROR

# 查看具体 MEDIA 相关的日志
grep "MEDIA:" /var/log/gateway.log
```

**Step 3：验证文件路径**
- 检查文件是否真实存在
- 检查路径格式是否正确（是否以 `/` 或 `~/` 开头）
- 检查文件是否可读

**Step 4：检查 Bot 状态**
- token 是否有效
- Bot 是否在线

### 3.4 常见错误及解决方案

| 错误 | 原因 | 解决方案 |
|------|------|----------|
| `FileNotFoundError: [Errno 2] No such file` | 文件不存在或路径解析错误 | 确认文件存在，检查 `MEDIA:` 标签后的路径格式 |
| `FileNotFoundError: 路径被替换成文本` | extract_media 正则 bug | 检查 base.py 的 `MEDIA_PATTERN` 是否已修复 |
| `nginx 404` | 文件路径在 gateway 侧不存在 | 确认文件在服务器上真实存在 |
| `TimeoutError` | 超时 | 检查 Bot 在线状态和 token 有效性 |
| `PermissionError` | 无读权限 | 检查文件权限 `ls -la /path/to/file` |

---

## 四、附件

### 4.1 修复代码位置

- **文件：** `base.py`
- **函数：** `extract_media()`
- **修复内容：** `MEDIA_PATTERN` 正则 + 前缀检查 + 文件存在性验证

### 4.2 相关日志路径（参考）

- Gateway 日志：`/var/log/gateway.log`
- Nginx 日志：`/var/log/nginx/access.log` / `error.log`

---

**报告结束。**

如音
2026-04-26
