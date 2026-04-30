# Agent记忆机制优化实施落地方案

> 创建时间：2026-04-30
> 版本：v1.2
> 负责人：如音
> 用途：将《多Agent记忆机制优化实施方案》细化为可逐项落地、可验收的完整操作手册
>
> 变更记录：
> - v1.2：Skill索引机制改为 Native Only + Metadata in SKILL.md（L1/L2实施章节对应修订）
> - v1.1：修正记忆路径——银月（main-agent）记忆在 `~/.hermes/memory/`，其他人（含如音/思月/紫灵）在 `~/.hermes/profiles/{name}/memories/`

---

## 一、整体架构

```
三层记忆架构：
├── 第一层：会话级（LLM context window，自动管理）
├── 第二层：中期记忆（memories/YYYY-MM-DD.md，每日日志）
└── 第三层：长期记忆（MEMORY.md + USER.md，字符限额 + 心跳巡检）

各姐妹记忆路径（重要差异）：
├── 银月（main-agent）：~/.hermes/memory/
├── 如音/思月/紫灵：~/.hermes/profiles/{name}/memories/
└── 公共配置：~/.hermes/profiles/shared/

支撑系统：
├── Skill索引体系（Native Only + Metadata in SKILL.md，metadata 按需读取）
├── 分工防护硬拦截（owner校验 + 豁免审批）
├── 心跳巡检Cronjob（各姐妹独立 + 1个全局汇总）
└── sub-agent信任积分（积分联动权限）
```

---

## 二、落地清单总览

| 层级 | 事项 | 落地内容 | 状态 | 验收标准 |
|------|------|---------|------|---------|
| **P0** | **L0** | **各姐妹精简自己的MEMORY.md**（按模板 ≤1800字符） | 待落地 | 字符数 <1800，可正常加载 |
| P0 | L1 | 批量补充 metadata（owner、trigger_scenes）到已有 SKILL.md | 待落地 | metadata.owner 非空，metadata.trigger_scenes 已填充 |
| P0 | L2 | 手工校正 metadata.owner（如音/思月/紫灵专属skill归属确认） | 待落地 | 所有条目 owner 非空 |
| **P1** | **L3-a** | **创建巡检Cronjob**（各姐妹每日21:00） | 待落地 | Cron创建成功，次日有日志输出 |
| P1 | L3-b | 初始化 MEMORY.md 索引摘要（启动时同步索引） | 待落地 | 各姐妹MEMORY.md含索引表 |
| P1 | L3-c | 固化启动时读取日志流程（写MEMORY.md） | 待落地 | 新session读取近3日日志 |
| P1 | L3-d | 固化任务交接写入日志流程（写MEMORY.md） | 待落地 | 交接时日志有记录 |
| **P2** | **L4** | **硬拦截逻辑**（owner校验） | 待落地 | 调用非shared skill被拦截 |
| P2 | L5 | hermes-memory-maintenance cronjob（全局汇总） | 待落地 | 每日09:00输出巡检报告 |
| P2 | L6 | 豁免审批流程（飞书消息 + 按钮交互） | 待落地 | 拦截后飞书收到审批消息 |

---

## 三、路径速查表

| 姐妹 | MEMORY.md 路径 | USER.md 路径 | memories/ 目录 | SOUL.md 路径 |
|------|---------------|-------------|--------------|-------------|
| 银月 | `~/.hermes/memory/MEMORY.md` | `~/.hermes/memory/USER.md` | `~/.hermes/memories/` | `~/.hermes/memory/SOUL.md` |
| 如音 | `~/.hermes/profiles/xingruyin/memories/MEMORY.md` | `~/.hermes/profiles/xingruyin/memories/USER.md` | `~/.hermes/profiles/xingruyin/memories/` | `~/.hermes/profiles/xingruyin/SOUL.md` |
| 思月 | `~/.hermes/profiles/wensiyue/memories/MEMORY.md` | `~/.hermes/profiles/wensiyue/memories/USER.md` | `~/.hermes/profiles/wensiyue/memories/` | `~/.hermes/profiles/wensiyue/SOUL.md` |
| 紫灵 | `~/.hermes/profiles/ziling/memories/MEMORY.md` | `~/.hermes/profiles/ziling/memories/USER.md` | `~/.hermes/profiles/ziling/memories/` | `~/.hermes/profiles/ziling/SOUL.md` |
| 公共 | `~/.hermes/profiles/shared/role-responsibility.md` | — | — | — |

**注意**：
- 银月（main-agent）使用 `~/.hermes/memory/`（无 `profiles/` 中间层）
- 其他姐妹（sub-agent）使用 `~/.hermes/profiles/{name}/memories/`（注意是两级嵌套）
- 中期日志路径均为 `{对应memories目录}/YYYY-MM-DD.md`

---

## 四、L0 实施：MEMORY.md 精简（P0，前置条件）

### 4.1 精简目标

各姐妹 MEMORY.md 按以下模板精简，目标 ≤1800 字符（保留压缩缓冲空间）：

```markdown
# {姐妹名} - 记忆档案

## 老大信息
- 身份/位置/沟通偏好（精简，不超过 3 行）

## 分工边界
- 我的职责：...
- 其他姐妹职责：...

## 技术环境
- 关键路径/工具/规范（精简，不超过 5 行）

## 重要规范
- 本项目中经确认必须遵守的规则（精简，不超过 5 条）

---

*由心跳机制维护，自动更新*
```

### 4.2 各姐妹精简命令

```bash
# 如音
wc -c ~/.hermes/profiles/xingruyin/memories/MEMORY.md
wc -l ~/.hermes/profiles/xingruyin/memories/MEMORY.md

# 思月
wc -c ~/.hermes/profiles/wensiyue/memories/MEMORY.md
wc -l ~/.hermes/profiles/wensiyue/memories/MEMORY.md

# 紫灵
wc -c ~/.hermes/profiles/ziling/memories/MEMORY.md
wc -l ~/.hermes/profiles/ziling/memories/MEMORY.md

# 银月（特殊路径）
wc -c ~/.hermes/memory/MEMORY.md
wc -l ~/.hermes/memory/MEMORY.md
```

### 4.3 验收标准

- [ ] 如音/思月/紫灵 MEMORY.md ≤1800 字符（路径：`~/.hermes/profiles/{name}/memories/MEMORY.md`）
- [ ] 银月 MEMORY.md ≤1800 字符（路径：`~/.hermes/memory/MEMORY.md`）
- [ ] 加载时无"超出上下文"警告
- [ ] 包含启动流程章节（读取日志）

---

## 五、L1 实施：批量补充 metadata 到 SKILL.md（P0）

### 5.1 方案说明

Native Only + Metadata in SKILL.md 方案下，无需独立 `skills-index.json`。优化数据（owner、trigger_scenes、match_stats、inferred_triggers）直接写入各 SKILL.md 的 frontmatter.metadata。

本步骤用脚本批量扫描所有 SKILL.md，为缺少 metadata 的 skill 补充初始结构。

### 5.2 批量补充脚本

```bash
#!/bin/bash
# ~/.hermes/scripts/init-skills-metadata.sh
# 批量为所有 SKILL.md 补充 frontmatter.metadata 字段

SKILLS_DIR="$HOME/.hermes/skills"

find "$SKILLS_DIR" -name "SKILL.md" | sort | while read sk; do
  skill_name=$(basename "$(dirname "$sk")")
  category=$(basename "$(dirname "$(dirname "$sk")")")

  echo "处理: $skill_name ($category)"

  # 检查是否已有 metadata
  if grep -q "^metadata:" "$sk" 2>/dev/null; then
    echo "  → 已有 metadata，跳过"
    continue
  fi

  # 推断 owner
  case "$category" in
    software-development|mlops|devops|github|gaming)
      owner="xingruyin" ;;
    productivity)
      owner="wensiyue" ;;
    research)
      owner="ziling" ;;
    autonomous-ai-agents|media|social-media|smart-home|red-teaming)
      owner="shared" ;;
    *)
      owner="shared" ;;
  esac

  # 追加 metadata 到 frontmatter（YAML block）
  # 在 --- 行之后、# skill title 之前插入
  python3 << EOF
import re

with open("$sk", "r") as f:
  content = f.read()

metadata_block = """metadata:
  owner: $owner
  trigger_scenes: []
  inferred_triggers: []
  dependencies: []
  match_stats:
    total: 0
    true_positive: 0
    false_positive: 0
    last_used: null
"""

# 找到第一个 --- 之后的位置插入
parts = content.split("---", 2)
if len(parts) >= 3:
  new_content = parts[0] + "---" + parts[1] + "---" + metadata_block + parts[2]
  with open("$sk", "w") as f:
    f.write(new_content)
  print("  → metadata 补充完成")
else:
  print("  → SKILL.md 格式异常，跳过")
EOF
done
```

### 5.3 执行命令

```bash
chmod +x ~/.hermes/scripts/init-skills-metadata.sh
mkdir -p ~/.hermes/scripts
~/.hermes/scripts/init-skills-metadata.sh

# 验证：检查已有 metadata 的数量
echo "=== 验证 ==="
total=$(find ~/.hermes/skills -name "SKILL.md" | wc -l)
with_meta=$(grep -l "^metadata:" ~/.hermes/skills/*/SKILL.md 2>/dev/null | wc -l)
echo "总 skill 数：$total"
echo "已有 metadata：$with_meta"
```

### 5.4 验收标准

- [ ] `~/.hermes/skills/` 下所有 SKILL.md 均含 `metadata.owner` 字段
- [ ] `metadata.owner` 预填值符合推断规则（shared/如音/思月/紫灵）
- [ ] `metadata.trigger_scenes` 初始化为空列表 `[]`（待 L1b 补充）
- [ ] `metadata.match_stats` 初始化为零值

---

## 六、L1b 实施：AI 批量补充 trigger_scenes（P0）

### 6.1 说明

trigger_scenes 是中文触发场景，对中文匹配至关重要。空列表由 AI 读取 SKILL.md 全文后自动补充。

### 6.2 批量补充命令

```bash
#!/bin/bash
# ~/.hermes/scripts/extract-triggers.sh
# 读取所有 SKILL.md，提取 trigger_scenes 并回填

SKILLS_DIR="$HOME/.hermes/skills"

for sk in $(find "$SKILLS_DIR" -name "SKILL.md"); do
  skill_name=$(basename "$(dirname "$sk")")
  echo "=== $skill_name ==="

  # 读取 SKILL.md 全文（限制前 4000 字符）
  content=$(head -c 4000 "$sk")

  # AI 提取（使用当前 session 的 LLM）
  # 这里输出 prompt，实际执行由 agent 完成
  echo "$content" | head -50
  echo "..."
done
```

> **说明**：trigger_scenes 的 AI 提取由巡检 cronjob 在每日 03:00 自动执行。本步骤仅确保 metadata 结构存在。

### 6.3 验收标准

- [ ] 所有 SKILL.md 含 `metadata.trigger_scenes` 字段（空列表亦可）
- [ ] 巡检启动后，非空 trigger_scenes 数量 ≥ 10

---

## 七、L2 实施：手工校正 metadata.owner（P0）

### 7.1 补充原则

| category 前缀 | 推断 owner（预填） | 需手工确认 |
|--------------|-------------------|-----------|
| `software-development` / `mlops` / `devops` / `github` / `gaming` | `xingruyin` | 是 |
| `productivity`（docs/powerpoint/note-taking相关） | `wensiyue` | 是 |
| `research`（需求/创意/ideation） | `ziling` | 是 |
| `autonomous-ai-agents` / `media` / `social-media` / `smart-home` / `red-teaming` | `shared` | 否 |
| 跨职能通用 | `shared` | 否 |

### 7.2 执行方式

银月手工编辑 `~/.hermes/skills/<category>/<skill>/SKILL.md`，修正 `metadata.owner` 值。

**查看当前 owner 分布**：
```bash
echo "=== 各 owner 数量 ==="
for f in ~/.hermes/skills/*/SKILL.md; do
  owner=$(awk '/^metadata:/,/^[^ ]/{if(/^  owner:/)print $2}' "$f" 2>/dev/null)
  echo "$owner"
done | sort | uniq -c | sort -rn
```

**查看需要确认的条目（owner = xingruyin/wensiyue/ziling）**：
```bash
echo "=== 如音专属（需确认）==="
grep -rl "owner: xingruyin" ~/.hermes/skills/*/SKILL.md | while read f; do
  echo "  $(basename $(dirname $f))"
done
```

### 7.3 验收标准

- [ ] 所有条目 `metadata.owner` 非空
- [ ] `metadata.owner` 只能是：`xingruyin`、`ziling`、`wensiyue`、`shared`
- [ ] 人工确认各专属skill归属正确

---

## 八、L3-a 实施：创建巡检Cronjob（P1）

### 8.1 各姐妹独立巡检Cronjob

**触发时间**：每天 21:00（北京时间）

**执行内容**：
1. 读取各自 `memories/` 近 3 天日志（银月在 `~/.hermes/memories/`，其他人在 `~/.hermes/profiles/{name}/memories/`）
2. 检查 MEMORY.md 当前字符数
   - 若超过 1800 字符 → 执行压缩（清理失效记录、精简表述）
   - 若不超过 1800 字符 → 本次跳过压缩
   - 若连续 3 次无需压缩 → 提示老大考虑将长规范迁移为 skill
3. 将巡检结果写入 `{对应memories目录}/YYYY-MM-DD巡检.md`

**创建命令（示例，如音）**：

```bash
# 如音的巡检 Cron
hermes cron create \
  --name "如音-记忆巡检" \
  --profile xingruyin \
  --message "执行如音记忆巡检任务：
1. 读取 ~/.hermes/profiles/xingruyin/memories/ 近3天日志
2. 检查 MEMORY.md 当前字符数（目标 ≤1800）
3. 若超过1800字符，执行精简压缩
4. 若连续3次无需压缩，提示老大将长规范迁移为skill
5. 将巡检结果写入 memories/YYYY-MM-DD巡检.md" \
  --schedule "0 21 * * *" \
  --deliver origin
```

**同步为思月、紫灵创建**（仅修改 profile name 和 agent 名）：

```bash
# 思月的巡检 Cron
hermes cron create \
  --name "思月-记忆巡检" \
  --profile wensiyue \
  --message "执行思月记忆巡检任务：
1. 读取 ~/.hermes/profiles/wensiyue/memories/ 近3天日志
2. 检查 MEMORY.md 当前字符数（目标 ≤1800）
3. 若超过1800字符，执行精简压缩
4. 若连续3次无需压缩，提示老大将长规范迁移为skill
5. 将巡检结果写入 memories/YYYY-MM-DD巡检.md" \
  --schedule "0 21 * * *" \
  --deliver origin

# 紫灵的巡检 Cron
hermes cron create \
  --name "紫灵-记忆巡检" \
  --profile ziling \
  --message "执行紫灵记忆巡检任务：
1. 读取 ~/.hermes/profiles/ziling/memories/ 近3天日志
2. 检查 MEMORY.md 当前字符数（目标 ≤1800）
3. 若超过1800字符，执行精简压缩
4. 若连续3次无需压缩，提示老大将长规范迁移为skill
5. 将巡检结果写入 memories/YYYY-MM-DD巡检.md" \
  --schedule "0 21 * * *" \
  --deliver origin
```

### 8.2 验收标准

- [ ] 三个姐妹各有一条 cronjob
- [ ] `hermes cron list` 可查到3条巡检cron
- [ ] 触发时间均为 `0 21 * * *`
- [ ] 次日检查对应 `memories/` 目录有巡检日志输出（银月：`~/.hermes/memories/`，如音/思月/紫灵：`~/.hermes/profiles/{name}/memories/`）

---

## 九、L3-b 实施：MEMORY.md 索引摘要初始化（P1）

### 9.1 生成索引摘要脚本

```bash
#!/bin/bash
# ~/.hermes/scripts/sync-skills-index-to-memory.sh
# 将 skills-index.json 关键字段同步到各MEMORY.md索引区

INDEX_FILE="$HOME/.hermes/skills-index/skills-index.json"

# 各姐妹MEMORY.md路径（银月特殊，其他人在两级memories/下）
declare -A MEMORY_FILES=(
  ["yinyue"]="$HOME/.hermes/memory/MEMORY.md"
  ["xingruyin"]="$HOME/.hermes/profiles/xingruyin/memories/MEMORY.md"
  ["wensiyue"]="$HOME/.hermes/profiles/wensiyue/memories/MEMORY.md"
  ["ziling"]="$HOME/.hermes/profiles/ziling/memories/MEMORY.md"
)

for profile in yinyue xingruyin wensiyue ziling; do
  MEMORY_FILE="${MEMORY_FILES[$profile]}"
  echo "处理 $profile -> $MEMORY_FILE"

  python3 << EOF
import json

with open("$INDEX_FILE") as f:
    d = json.load(f)

by_owner = {}
for s in d['skills']:
    o = s.get('owner', 'shared')
    by_owner.setdefault(o, []).append(s)

lines = ["## Skill索引摘要", "", "| name | category | owner | 用途 |", "|------|----------|-------|------|"]
for s in by_owner.get('$profile', []) + by_owner.get('shared', []):
    purpose = s.get('purpose', '')[:40]
    lines.append(f"| {s['name']} | {s['category']} | {s['owner']} | {purpose} |")

print('\n'.join(lines))
EOF
done
```

> **说明**：由于各姐妹MEMORY.md结构不同，索引摘要写入位置由各姐妹自行决定。建议写在「技术环境」之后单独成节，控制在200字符以内。银月的MEMORY.md在 `~/.hermes/memory/MEMORY.md`，同步脚本需单独处理。

### 9.2 验收标准

- [ ] 如音/思月/紫灵/银月各 MEMORY.md 含 `## Skill索引摘要` 章节
- [ ] 索引摘要包含该姐妹专属skill + shared skill
- [ ] 字符数控制在200字符以内（避免加剧MEMORY.md空间压力）

---

## 十、L3-c 实施：固化启动时读取日志流程（P1）

### 10.1 在 MEMORY.md 中固化

**如音/思月/紫灵**（在各自 MEMORY.md 开头添加）：

```markdown
## 启动流程
每次启动时：
1. 读取 memories/ 目录下近 3 天的日志文件
2. 从日志中提取「进行中」和「待处理」事项
3. 若有未完成的上文任务，主动询问老大是否接续
4. 额外读取 ~/.hermes/profiles/shared/role-responsibility.md，作为记忆的一部分
```

**银月**（在 `~/.hermes/memory/MEMORY.md` 开头添加）：

```markdown
## 启动流程
每次启动时：
1. 读取 ~/.hermes/memories/ 目录下近 3 天的日志文件
2. 从日志中提取「进行中」和「待处理」事项
3. 若有未完成的上文任务，主动询问老大是否接续
4. 额外读取 ~/.hermes/profiles/shared/role-responsibility.md，作为记忆的一部分
```

> **注意**：银月的 `memories/` 路径在 `~/.hermes/memories/`（直接在 hermes 下），如音/思月/紫灵的在 `~/.hermes/profiles/{name}/memories/`。

**验证方式**：重启某姐妹session，观察是否在回复前读取了日志文件。

### 10.2 验收标准

- [ ] 各 MEMORY.md 含「启动流程」章节（银月在 `~/.hermes/memory/MEMORY.md`，其他人含路径）
- [ ] 章节内容包含上述4条
- [ ] 新session启动后发送测试消息，验证日志读取行为

---

## 十一、L3-d 实施：固化任务交接写入日志流程（P1）

### 11.1 在 MEMORY.md 中固化

在各姐妹 MEMORY.md「重要规范」章节后添加：

```markdown
## 任务交接规范
当姐妹之间需要交接任务时，交出方必须写入日志：
- 当前进度：...
- 关键信息：...
- 注意事项：...
- 接替者需要：...
```

### 11.2 验收标准

- [ ] 各 MEMORY.md 含「任务交接规范」章节（银月在 `~/.hermes/memory/MEMORY.md`，其他人在 `~/.hermes/profiles/{name}/memories/MEMORY.md`）
- [ ] 下次实际任务交接时，日志中有对应记录

---

## 十二、L4 实施：硬拦截逻辑（P2）

### 12.1 拦截规则

```
银月尝试调用 [skill-name]
    │
    ▼
skill_view() 加载 SKILL.md → 读取 metadata.owner
    │
    ├── owner = shared → 允许调用
    │
    └── owner = 如音/紫灵/思月 → 直接拒绝
        │
        ▼
┌─────────────────────────────────────┐
│ ❌ 调用被拦截                         │
│─────────────────────────────────────│
│ [skill-name] 归属：如音专属           │
│ 不允许直接调用                        │
│                                  │
│ 请通过 delegate_task 委托如音执行     │
└─────────────────────────────────────┘
```

### 12.2 实施位置

硬拦截逻辑在银月的 skill 调用入口实现。metadata.owner 在 `skill_view()` 读取 SKILL.md 时按需获取，无需独立索引文件。

**实现伪代码**（由银月/网关侧执行）：

```python
def call_skill(skill_name, caller_agent):
    # 1. 读取 SKILL.md frontmatter.metadata
    skill_md_path = f"~/.hermes/skills/{skill_name}/SKILL.md"
    frontmatter = parse_yaml_frontmatter(skill_md_path)
    owner = frontmatter.get("metadata", {}).get("owner", "shared")

    # 2. 校验 owner
    if owner == "shared":
        return execute_skill(skill_name)
    elif owner == caller_agent:
        return execute_skill(skill_name)  # 自己调用自己，可以
    else:
        # 触发豁免审批流程（L6）
        return trigger_exemption_flow(skill_name, caller_agent)
```

### 12.3 豁免条件

| 场景 | 处理方式 |
|------|---------|
| sub-agent 在线 | 飞书推送审批请求，等待 [批准]/[拒绝] |
| sub-agent 离线/忙碌 | 自动豁免（单次有效，记录bypass.log） |
| 紧急情况（老大强指） | 老大直接覆盖，记录audit.log |

### 12.4 验收标准

- [ ] 银月尝试直接调用如音专属skill（如 `systematic-debugging`）时返回拦截提示
- [ ] 银月调用shared skill（如 `agent-delegate`）时正常执行
- [ ] 拦截记录写入 `~/.hermes/logs/bypass.log`

---

## 十三、L5 实施：hermes-memory-maintenance cronjob（P2）

### 13.1 Cronjob 配置

**触发时间**：每天 03:00（北京时间）

**执行用户**：银月（main-agent）

```bash
hermes cron create \
  --name "Hermes-记忆库全局巡检" \
  --profile yinyue \
  --message "执行记忆库全局巡检：
1. rglob扫描 ~/.hermes/skills/ 下所有 SKILL.md，检查 metadata 完整性
2. 读取 ~/.hermes/logs/bypass.log，统计拦截次数
3. 计算各 sub-agent 积分（基于本周操作日志）
4. 生成巡检报告，推送飞书
5. 发现未归档内容 → 通知思月" \
  --schedule "0 3 * * *" \
  --deliver origin
```

### 13.3 验收标准

- [ ] `hermes cron list` 查得到该cronjob
- [ ] 每天09:00输出巡检日志（推送飞书）
- [ ] 周报每7天推送一次

---

## 十四、L6 实施：豁免审批流程（P2）

### 14.1 飞书审批消息

```json
{
  "msg_type": "interactive",
  "card": {
    "header": {
      "title": { "tag": "plain_text", "content": "⚠️ Skill调用审批请求" },
      "template": "orange"
    },
    "elements": [
      { "tag": "div", "content": { "tag": "lark_md", "content": "**银月申请调用** `[skill-name]`\n**原因**：`[银月填写]`\n**归属**：如音专属skill" } },
      { "tag": "action", "actions": [
        { "tag": "button", "text": { "tag": "plain_text", "content": "✅ 批准" }, "action_type": "primary", "value": { "action": "approve", "skill": "[skill-name]" } },
        { "tag": "button", "text": { "tag": "plain_text", "content": "❌ 拒绝" }, "action_type": "danger", "value": { "action": "reject", "skill": "[skill-name]" } }
      ]}
    ]
  }
}
```

### 14.2 按钮回调处理

- **批准**：写入 `bypass.log`，允许本次调用
- **拒绝**：拒绝调用，告知银月
- **超时5分钟**：自动批准（计入统计，标注「超时自动批准」）

### 14.3 验收标准

- [ ] 触发硬拦截后，飞书收到审批card消息
- [ ] 点击 [批准] 后，skill正常执行
- [ ] 点击 [拒绝] 后，skill不执行并告知银月
- [ ] 5分钟无操作后自动批准

---

## 十五、落地里程碑

```
Milestone 1（P0 完成标志）：L0 + L1 + L1b + L2 完成
  → 技能：所有 SKILL.md 含 metadata.owner + metadata.trigger_scenes
  → 记忆：各MEMORY.md ≤1800字符（含银月特殊路径）

Milestone 2（P1 完成标志）：L3-a/b/c/d 完成
  → 自动化：每日21:00巡检cron运行
  → 启动：各MEMORY.md含启动流程和任务交接规范
  → 索引：各MEMORY.md含skill索引摘要（Native Only）

Milestone 3（P2 完成标志）：L4 + L5 + L6 完成
  → 安全：分工硬拦截生效（读取SKILL.md metadata.owner）
  → 运维：全局巡检cron（03:00）+ 周报运行
  → 审批：豁免流程可交互
```

---

## 十六、验收总检查清单

### P0（前置）
- [ ] 如音 MEMORY.md ≤1800 字符（路径：`~/.hermes/profiles/xingruyin/memories/MEMORY.md`）
- [ ] 思月 MEMORY.md ≤1800 字符（路径：`~/.hermes/profiles/wensiyue/memories/MEMORY.md`）
- [ ] 紫灵 MEMORY.md ≤1800 字符（路径：`~/.hermes/profiles/ziling/memories/MEMORY.md`）
- [ ] 银月 MEMORY.md ≤1800 字符（路径：`~/.hermes/memory/MEMORY.md`）
- [ ] 所有 SKILL.md 含 `metadata.owner`（非空）
- [ ] 所有 SKILL.md 含 `metadata.trigger_scenes`（可为空列表）
- [ ] `metadata.owner` 归属正确（shared/如音/思月/紫灵）

### P1（核心自动化）
- [ ] 3条独立巡检cron创建成功（21:00）
- [ ] 次日各 memories/ 目录有巡检日志输出（银月：`~/.hermes/memories/`，其他人在 `~/.hermes/profiles/{name}/memories/`）
- [ ] 各 MEMORY.md 含启动流程章节（银月路径特殊）
- [ ] 各 MEMORY.md 含任务交接规范章节
- [ ] 各 MEMORY.md 含 Skill 索引摘要章节

### P2（配套功能）
- [ ] 调用非shared skill被硬拦截
- [ ] bypass.log 记录拦截事件
- [ ] 全局巡检cron（09:00）创建成功
- [ ] 周报每7天推送一次
- [ ] 飞书审批card消息可正常收发
- [ ] 批准/拒绝按钮回调正常

---

> 关联文档：
> - [[多Agent记忆机制优化方案]] — 记忆机制主文档
> - [[Agent委托协作机制]] — Agent 委托协作标准流程
> - [[Skill管理机制]] — Skill索引体系与分工防护
> - [[记忆系统]] — Hermes 原生记忆机制说明
> - [[Obsidian文档管理流程v1.0]] — 思月归档流程
