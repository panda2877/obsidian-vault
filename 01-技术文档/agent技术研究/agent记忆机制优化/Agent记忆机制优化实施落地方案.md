# Agent记忆机制优化实施落地方案

> 创建时间：2026-04-30
> 版本：v1.0
> 负责人：如音
> 用途：将《多Agent记忆机制优化实施方案》细化为可逐项落地、可验收的完整操作手册
>
> 变更记录：
> - v1.0：细化所有待落地事项（L1-L6），每个事项补充具体命令/脚本/验证节点；按 P0/P1/P2 重新排布落地顺序；新增验收标准章节

---

## 一、整体架构

```
三层记忆架构：
├── 第一层：会话级（LLM context window，自动管理）
├── 第二层：中期记忆（memories/YYYY-MM-DD.md，每日日志）
└── 第三层：长期记忆（MEMORY.md + USER.md，字符限额 + 心跳巡检）

支撑系统：
├── Skill索引体系（skills-index.json + MEMORY.md索引摘要）
├── 分工防护硬拦截（owner校验 + 豁免审批）
├── 心跳巡检Cronjob（各姐妹独立 + 1个全局汇总）
└── sub-agent信任积分（积分联动权限）
```

---

## 二、落地清单总览

| 层级 | 事项 | 落地内容 | 状态 | 验收标准 |
|------|------|---------|------|---------|
| **P0** | **L0** | **各姐妹精简自己的MEMORY.md**（按模板 ≤1800字符） | 待落地 | 字符数 <1800，可正常加载 |
| P0 | L1 | 初始化 skills-index.json（扫描 + 生成JSON索引） | 待落地 | JSON可读，条目数量与skills/目录一致 |
| P0 | L2 | 手工补充 owner 归属（银月填写） | 待落地 | 所有条目owner非空 |
| **P1** | **L3-a** | **创建巡检Cronjob**（各姐妹每日21:00） | 待落地 | Cron创建成功，次日有日志输出 |
| P1 | L3-b | 初始化 MEMORY.md 索引摘要（启动时同步索引） | 待落地 | 各姐妹MEMORY.md含索引表 |
| P1 | L3-c | 固化启动时读取日志流程（写MEMORY.md） | 待落地 | 新session读取近3日日志 |
| P1 | L3-d | 固化任务交接写入日志流程（写MEMORY.md） | 待落地 | 交接时日志有记录 |
| **P2** | **L4** | **硬拦截逻辑**（owner校验） | 待落地 | 调用非shared skill被拦截 |
| P2 | L5 | hermes-memory-maintenance cronjob（全局汇总） | 待落地 | 每日09:00输出巡检报告 |
| P2 | L6 | 豁免审批流程（飞书消息 + 按钮交互） | 待落地 | 拦截后飞书收到审批消息 |

---

## 三、L0 实施：MEMORY.md 精简（P0，前置条件）

### 3.1 精简目标

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

### 3.2 各姐妹精简检查

| 姐妹 | 当前MEMORY.md字符数 | 目标 | 状态 |
|------|-------------------|------|------|
| 如音 | ~1750（见原方案第5章） | ≤1800 | ⚠️ 临界，需精简 |
| 思月 | 待确认 | ≤1800 | 待查 |
| 紫灵 | 待确认 | ≤1800 | 待查 |

**精简命令**（各姐妹执行）：
```bash
# 查看当前字符数
wc -c ~/.hermes/profiles/{name}/MEMORY.md

# 确认行数
wc -l ~/.hermes/profiles/{name}/MEMORY.md
```

### 3.3 验收标准

- [ ] 各姐妹 MEMORY.md ≤1800 字符
- [ ] 加载时无"超出上下文"警告
- [ ] 包含启动流程章节（读取日志）

---

## 四、L1 实施：初始化 skills-index.json（P0）

### 4.1 扫描脚本

```bash
#!/bin/bash
# ~/.hermes/scripts/generate-skills-index.sh

SKILLS_DIR="$HOME/.hermes/skills"
INDEX_FILE="$HOME/.hermes/skills-index/skills-index.json"
INDEX_MD="$HOME/.hermes/skills-index/skills-index.md"

mkdir -p "$(dirname "$INDEX_FILE")"

# 生成 JSON
echo '{' > "$INDEX_FILE"
echo '  "version": "2026-04-30",' >> "$INDEX_FILE"
echo '  "skills": [' >> "$INDEX_FILE"

first=true
find "$SKILLS_DIR" -name "SKILL.md" | sort | while read sk; do
  dir=$(dirname "$sk")
  skill_name=$(basename "$dir")
  category=$(basename "$(dirname "$dir")")
  
  # 提取description（取第一段非标题内容）
  desc=$(sed -n '/^# /d; /^$/d; /^[>]/d; p' "$sk" | head -3 | tr '\n' ' ' | sed 's/"/\\"/g' | cut -c1-120)
  [ -z "$desc" ] && desc="待补充"

  # 提取trigger_scenes（如有）
  trigger=$(grep -A 20 "^trigger_scenes\|^## Trigger\|^### 触发" "$sk" 2>/dev/null | grep -E "^\s*[-*]|\"" | head -5 | sed 's/.*[:：]\s*//; s/"/\\"/g' | tr '\n' ',' | sed 's/,$//')
  [ -z "$trigger" ] && trigger=""

  if [ "$first" = true ]; then
    first=false
  else
    echo ',' >> "$INDEX_FILE"
  fi

  cat >> "$INDEX_FILE" <<EOF
    {
      "name": "$skill_name",
      "path": "$category/$skill_name",
      "owner": "shared",
      "category": "$category",
      "purpose": "$desc",
      "trigger_scenes": [$([ -n "$trigger" ] && echo "\"$(echo $trigger | sed 's/,/\",\"/g')\"" || echo "")],
      "keywords": [],
      "dependencies": [],
      "last_updated": "2026-04-30"
    }
EOF
done

echo '' >> "$INDEX_FILE"
echo '  ]' >> "$INDEX_FILE"
echo '}' >> "$INDEX_FILE"

echo "✅ skills-index.json 生成完成"
echo "   条目数：$(grep '"name":' "$INDEX_FILE" | wc -l)"
```

### 4.2 执行命令

```bash
chmod +x ~/.hermes/scripts/generate-skills-index.sh
mkdir -p ~/.hermes/scripts ~/.hermes/skills-index
~/.hermes/scripts/generate-skills-index.sh

# 验证
cat ~/.hermes/skills-index/skills-index.json | python3 -m json.tool > /dev/null && echo "✅ JSON格式正确"
```

### 4.3 验收标准

- [ ] `~/.hermes/skills-index/skills-index.json` 存在且为合法JSON
- [ ] `skills-index.json` 条目数 == `find ~/.hermes/skills/ -name "SKILL.md" | wc -l`
- [ ] 所有条目的 `owner` 字段值 = `"shared"`（待L2补充）
- [ ] `python3 -m json.tool skills-index.json` 无报错

---

## 五、L2 实施：手工补充 owner 归属（P0）

### 5.1 补充原则

| category 前缀 | 推断 owner |
|--------------|-----------|
| `software-development` / `mlops` / `devops` / `github` / `gaming` | `xingruyin`（如音） |
| `productivity`（docs/powerpoint/note-taking相关） | `wensiyue`（思月） |
| `research`（需求/创意/ideation） | `ziling`（紫灵） |
| `autonomous-ai-agents` / `media` / `social-media` / `smart-home` / `red-teaming` | `shared`（共享） |
| 跨职能通用 | `shared` |

### 5.2 执行方式

银月手工编辑 `~/.hermes/skills-index/skills-index.json`，将所有 `owner` 为 `"shared"` 的条目按上表修正。

**命令**：
```bash
# 查看当前 owner 分布
cat ~/.hermes/skills-index/skills-index.json | python3 -c "
import json,sys
d=json.load(sys.stdin)
from collections import Counter
owners=Counter(s.get('owner','缺失') for s in d['skills'])
for k,v in owners.items(): print(f'{k}: {v}')
"

# 查看需要手工补充的条目
cat ~/.hermes/skills-index/skills-index.json | python3 -c "
import json,sys
d=json.load(sys.stdin)
for s in d['skills']:
    if s.get('owner')=='shared':
        print(f\"  {s['name']} ({s['category']})\")
"
```

### 5.3 验收标准

- [ ] 所有条目 `owner` 非空
- [ ] `owner` 只能是：`xingruyin`、`ziling`、`wensiyue`、`shared`
- [ ] 人工确认各专属skill归属正确

---

## 六、L3-a 实施：创建巡检Cronjob（P1）

### 6.1 各姐妹独立巡检Cronjob

**触发时间**：每天 21:00（北京时间）

**执行内容**：
1. 读取 `memories/` 近 3 天日志
2. 检查 MEMORY.md 当前字符数
   - 若超过 1800 字符 → 执行压缩（清理失效记录、精简表述）
   - 若不超过 1800 字符 → 本次跳过压缩
   - 若连续 3 次无需压缩 → 提示老大考虑将长规范迁移为 skill
3. 将巡检结果写入 `memories/YYYY-MM-DD巡检.md`

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

### 6.2 验收标准

- [ ] 三个姐妹各有一条 cronjob
- [ ] `hermes cron list` 可查到3条巡检cron
- [ ] 触发时间均为 `0 21 * * *`
- [ ] 次日检查 `memories/` 目录有巡检日志输出

---

## 七、L3-b 实施：MEMORY.md 索引摘要初始化（P1）

### 7.1 生成索引摘要脚本

```bash
#!/bin/bash
# ~/.hermes/scripts/sync-skills-index-to-memory.sh
# 将 skills-index.json 关键字段同步到各姐妹 MEMORY.md 索引区

INDEX_FILE="$HOME/.hermes/skills-index/skills-index.json"
PROFILES_DIR="$HOME/.hermes/profiles"

# 为每个profile同步
for profile in xingruyin ziling wensiyue; do
  MEMORY_FILE="$PROFILES_DIR/$profile/MEMORY.md"
  
  # 提取该profile专属 + shared的skill，生成索引表
  python3 << EOF
import json

with open("$INDEX_FILE") as f:
    d = json.load(f)

# 按owner分类
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

> **说明**：由于各姐妹MEMORY.md结构不同，索引摘要写入位置由各姐妹自行决定。建议写在「技术环境」之后单独成节，控制在200字符以内。

### 7.2 验收标准

- [ ] 各姐妹 MEMORY.md 含 `## Skill索引摘要` 章节
- [ ] 索引摘要包含该姐妹专属skill + shared skill
- [ ] 字符数控制在200字符以内（避免加剧MEMORY.md空间压力）

---

## 八、L3-c 实施：固化启动时读取日志流程（P1）

### 8.1 在 MEMORY.md 中固化

在各姐妹 MEMORY.md 开头（紧跟标题之后）添加：

```markdown
## 启动流程
每次启动时：
1. 读取 memories/ 目录下近 3 天的日志文件
2. 从日志中提取「进行中」和「待处理」事项
3. 若有未完成的上文任务，主动询问老大是否接续
4. 额外读取 ~/.hermes/profiles/shared/role-responsibility.md，作为记忆的一部分
```

**验证方式**：重启某姐妹session，观察是否在回复前读取了日志文件。

### 8.2 验收标准

- [ ] 各姐妹 MEMORY.md 含「启动流程」章节
- [ ] 章节内容包含上述4条
- [ ] 新session启动后发送测试消息，验证日志读取行为

---

## 九、L3-d 实施：固化任务交接写入日志流程（P1）

### 9.1 在 MEMORY.md 中固化

在各姐妹 MEMORY.md「重要规范」章节后添加：

```markdown
## 任务交接规范
当姐妹之间需要交接任务时，交出方必须写入日志：
- 当前进度：...
- 关键信息：...
- 注意事项：...
- 接替者需要：...
```

### 9.2 验收标准

- [ ] 各姐妹 MEMORY.md 含「任务交接规范」章节
- [ ] 下次实际任务交接时，日志中有对应记录

---

## 十、L4 实施：硬拦截逻辑（P2）

### 10.1 拦截规则

```
银月尝试调用 [skill-name]
    │
    ▼
skill-index 校验 owner
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

### 10.2 实施位置

硬拦截逻辑在银月的 skill 调用入口实现（即 `delegate_task` 之前）。

**实现伪代码**（由银月/网关侧执行）：

```python
def call_skill(skill_name, caller_agent):
    # 1. 读取 skills-index.json
    skill_info = get_skill_info(skill_name)  # 包含 owner 字段
    
    # 2. 校验 owner
    if skill_info['owner'] == 'shared':
        return execute_skill(skill_name)
    elif skill_info['owner'] == caller_agent:
        return execute_skill(skill_name)  # 自己调用自己，可以
    else:
        # 触发豁免审批流程（L6）
        return trigger_exemption_flow(skill_name, caller_agent)
```

### 10.3 豁免条件

| 场景 | 处理方式 |
|------|---------|
| sub-agent 在线 | 飞书推送审批请求，等待 [批准]/[拒绝] |
| sub-agent 离线/忙碌 | 自动豁免（单次有效，记录bypass.log） |
| 紧急情况（老大强指） | 老大直接覆盖，记录audit.log |

### 10.4 验收标准

- [ ] 银月尝试直接调用如音专属skill（如 `systematic-debugging`）时返回拦截提示
- [ ] 银月调用shared skill（如 `agent-delegate`）时正常执行
- [ ] 拦截记录写入 `~/.hermes/logs/bypass.log`

---

## 十一、L5 实施：hermes-memory-maintenance cronjob（P2）

### 11.1 Cronjob 配置

**触发时间**：每天 09:00（北京时间）

**执行用户**：银月（main-agent）

```bash
hermes cron create \
  --name "Hermes-记忆库全局巡检" \
  --profile yinyue \
  --message "执行记忆库全局巡检：
1. 扫描 ~/.hermes/skills/ 目录，与 skills-index.json 比对一致性
2. 读取 ~/.hermes/logs/bypass.log，统计拦截次数
3. 计算各 sub-agent 积分（基于本周操作日志）
4. 生成巡检报告，推送飞书
5. 发现未归档内容 → 通知思月" \
  --schedule "0 9 * * *" \
  --deliver origin
```

### 11.2 巡检脚本内容框架

```bash
#!/bin/bash
# ~/.hermes/scripts/memory-maintenance.sh

echo "===== Hermes 记忆库巡检 $(date '+%Y-%m-%d %H:%M') ====="

# 1. 索引一致性检查
ACTUAL=$(find ~/.hermes/skills/ -name "SKILL.md" | wc -l)
INDEXED=$(python3 -c "import json; print(len(json.load(open('$HOME/.hermes/skills-index/skills-index.json'))['skills']))")

echo "[1] 索引一致性：实际 $ACTUAL vs 索引 $INDEXED"
[ "$ACTUAL" != "$INDEXED" ] && echo "  ⚠️ 不一致，需要同步"

# 2. bypass.log 统计
BYPASS_COUNT=$(grep -c "$(date '+%Y-%m-%d')" ~/.hermes/logs/bypass.log 2>/dev/null || echo 0)
echo "[2] 今日拦截次数：$BYPASS_COUNT"

# 3. 各 sub-agent 积分查询（读取积分文件）
for agent in xingruyin ziling wensiyue; do
  SCORE=$(cat "$HOME/.hermes/profiles/$agent/credit.score" 2>/dev/null || echo 100)
  echo "[3] $agent 积分：$SCORE"
done

echo "===== 巡检完成 ====="
```

### 11.3 周报格式（每7天一次）

```
═══════════════════════════════════════
Hermes Skill 索引巡检报告
时间：2026-04-30 周二 09:00
═══════════════════════════════════════

【1. 索引表一致性检查】
  • skills/ 目录总数：48
  • skills-index.json 条目数：48
  • 缺失索引：0
  • 异常条目：0
  • 状态：✅ 正常

【2. sub-agent 积分状态】
  • 如音：92分
  • 紫灵：88分
  • 思月：95分

【3. 违规拦截统计】
  • 本周拦截次数：3次
  • 本月累计：7次
  • 趋势：↓ 较上月减少 2 次

【4. 待补充 trigger_scenes】
  • github-auth（新建，缺少触发场景）
  • blogwatcher（缺少触发场景）

【5. 异常告警】
  • 无

═══════════════════════════════════════
```

### 11.4 验收标准

- [ ] `hermes cron list` 查得到该cronjob
- [ ] 每天09:00输出巡检日志（`--deliver origin` 推送飞书）
- [ ] 周报每7天推送一次（发送至飞书群）

---

## 十二、L6 实施：豁免审批流程（P2）

### 12.1 飞书审批消息格式

使用飞书 interactive card 消息：

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

### 12.2 按钮回调处理

- **批准**：写入 `bypass.log`，允许本次调用
- **拒绝**：拒绝调用，告知银月
- **超时5分钟**：自动批准（计入统计，标注「超时自动批准」）

### 12.3 验收标准

- [ ] 触发硬拦截后，飞书收到审批card消息
- [ ] 点击 [批准] 后，skill正常执行
- [ ] 点击 [拒绝] 后，skill不执行并告知银月
- [ ] 5分钟无操作后自动批准

---

## 十三、落地优先级与里程碑

```
Milestone 1（P0 完成标志）：L0 + L1 + L2 完成
  → 技能：skills-index.json 完整且owner已填写
  → 记忆：各姐妹MEMORY.md ≤1800字符

Milestone 2（P1 完成标志）：L3-a/b/c/d 完成
  → 自动化：每日21:00巡检cron运行
  → 启动：MEMORY.md含启动流程和任务交接规范
  → 索引：各MEMORY.md含skill索引摘要

Milestone 3（P2 完成标志）：L4 + L5 + L6 完成
  → 安全：分工硬拦截生效
  → 运维：全局巡检cron + 周报运行
  → 审批：豁免流程可交互
```

---

## 十四、验收总检查清单

### P0（前置）
- [ ] 各姐妹 MEMORY.md ≤1800 字符
- [ ] skills-index.json 存在且JSON合法
- [ ] skills-index.json 条目数与 skills/ 目录一致
- [ ] 所有条目 owner 非空，归属正确

### P1（核心自动化）
- [ ] 3条独立巡检cron创建成功（21:00）
- [ ] 次日 memories/ 有巡检日志输出
- [ ] 各 MEMORY.md 含启动流程章节
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
