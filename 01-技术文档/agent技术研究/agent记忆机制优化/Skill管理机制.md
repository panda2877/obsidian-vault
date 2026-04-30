# Skill管理机制

> 创建时间：2026-04-29
> 版本：v2.1
> 负责人：如音
> 用途：建立Skill索引体系、分工防护硬拦截、sub-agent信任积分机制
>
> 变更记录：
> - v2.1：Skill索引机制改为 Native Only + Metadata in SKILL.md 方案，废弃 skill-index-ext.json 独立索引层
> - v2.0：拆分自《多Agent记忆机制优化方案》，删除10.9待落地事项（已移至实施方案文档）

---

## 一、背景与目标

多Agent协作体系中，skill 作为核心能力单元，存在以下问题：
- skill 数量增长后难以快速定位
- 调用时未强制匹配最佳 skill
- 跨 Agent 分工边界模糊，容易绕过分工原则
- trigger_scenes / keywords 等元数据缺失或不完整

本方案旨在建立一套完整的 skill 管理机制，包括索引体系、调用规范、分工防护和持续优化。

---

## 二、索引机制

> 变更说明（v2.1）：原 skill-index-ext.json 独立索引层方案废弃，改用 **Native Only + Metadata in SKILL.md** 方案。优化数据直接写入各 SKILL.md 的 frontmatter.metadata，manifest 只注入标准字段，metadata 按需读取。详情见「九、已确认结论」。

### 2.1 设计原则

```
SKILL.md frontmatter
├── 标准字段（name, description, category, tags）
│     → 注入 system prompt manifest
│     → ~300 bytes/skill，manifest 总计 ~21KB
│
└── metadata 字段（owner, trigger_scenes, match_stats, inferred_triggers）
      → skill_view 读取时按需加载
      → 不进 manifest
      → 手动可直接编辑
      → 自动由 skill 执行后写回
```

### 2.2 SKILL.md 标准字段（注入 manifest）

| 字段 | 说明 | 必填 |
|------|------|------|
| `name` | skill名称，最大64字符 | 是 |
| `description` | 一句话描述，最大1024字符 | 是 |
| `category` | 职能分类，复用现有 category 体系 | 是 |
| `tags` | 关键词列表（英文为主，语义匹配用） | 是 |

### 2.3 SKILL.md metadata 字段（按需读取）

| 字段 | 说明 |
|------|------|
| `owner` | 归属：`xingruyin`（如音专属）、`ziling`（紫灵专属）、`wensiyue`（思月专属）、`shared`（共享） |
| `trigger_scenes` | 触发场景列表（中文，便于匹配中文任务描述） |
| `inferred_triggers` | AI 推理自动补全的触发词 |
| `dependencies` | 依赖的其他 skills |
| `match_stats` | 匹配质量追踪数据 |

**metadata 字段不进 manifest，按需读取。**

### 2.4 metadata 结构示例

```yaml
---
name: systematic-debugging
description: Bug排查、故障诊断、报错分析
category: software-development
tags: [bug, error, debugging, crash]
metadata:
  owner: xingruyin
  trigger_scenes:
    - Bug排查
    - 故障诊断
    - 报错分析
  inferred_triggers: []
  dependencies: []
  match_stats:
    total: 15
    true_positive: 13
    false_positive: 2
    last_used: "2026-04-28"
---
```

### 2.5 索引调用机制

```
任务描述输入
    │
    ▼
Native 匹配（system prompt manifest）
  ├── L1：category 精确匹配
  ├── L2：tags + description 语义模糊匹配（英文为主）
  └── L3：LLM 综合推理
    │
    ▼
命中 top-1 skill
    │
    ▼
skill_view() 加载 SKILL.md 全文
    │
    ▼
按需读取 metadata（不占 manifest）
  ├── owner 归属 → 分工校验
  ├── trigger_scenes → 中文补充匹配（中文输入时触发）
  └── match_stats → 记录使用结果
    │
    ▼
owner = shared → 自行加载执行
owner = 如音/紫灵/思月 → delegate_task 委托执行
```

### 2.6 trigger_scenes 补充匹配（中文场景）

| 时机 | 动作 |
|------|------|
| 命中 skill 后 | 读取 metadata.owner → 分工校验 |
| 用户输入含中文 | 读取 metadata.trigger_scenes → L2 中文匹配 |
| skill 执行完成 | 更新 metadata.match_stats → 写回 SKILL.md |

**扩展字段只在以上三个明确时机按需读取，平时零开销。**

---

## 三、分工防护机制

### 3.1 硬拦截

银月调用任何 skill 前，必须经过 skill-index 匹配。

```
银月尝试直接调用 [非shared skill]
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

### 3.2 豁免机制

当目标 sub-agent 不在线或不可用时，允许临时豁免：

```
银月尝试调用 [skill-name]
    │
    ▼
硬拦截触发
    │
    ├── sub-agent 在线 → 推送审批请求给 sub-agent
    │     │
    │     ▼
    │   sub-agent 收到飞书审批
    │   「银月申请调用 [skill-name]
    │    原因：[银月填写]
    │    [批准] [拒绝] [5分钟后自动批准]」
    │     │
    │     ▼
    │   批准 → 记录豁免 → 允许调用
    │   拒绝 → 拒绝调用
    │   超时 → 自动批准（计入统计）
    │
    └── sub-agent 离线/忙碌
          │
          ▼
        自动批准临时豁免（单次有效）
```

| 场景 | 有效期 | 说明 |
|------|--------|------|
| sub-agent 在线，审批通过 | 单次调用 | 记录在案，统计中 |
| sub-agent 离线/忙碌 | 单次调用 | 注明原因，不扣分 |

### 3.3 违规上报

- **实时上报**：每次拦截立即推送飞书给老大
- **每周巡检**：hermes-memory-maintenance cronjob 生成周报，包含拦截次数、趋势分析

---

## 四、sub-agent 信任积分机制

### 4.1 积分规则（仅针对 sub-agent）

| 操作 | 积分变化 |
|------|----------|
| 初始分 | 100 分 |
| 正常完成任务 | +0（维持） |
| 主动发现并修复 bug | +1 |
| 主动优化（性能/流程） | +1 |
| 任务超时/失败 | -2 |
| 主动绕过分工 | -10 |

下限：0 分（不会变负）

### 4.2 积分与权限联动

| 积分区间 | 权限状态 |
|----------|----------|
| ≥80 分 | 正常权限 |
| 60-79 分 | 高风险操作需审批（删除文件、跨分工操作、批量操作限流） |
| <60 分 | 所有关键操作需审批，调用频率限制（5次/分钟 → 2次/分钟） |

### 4.3 审批请求

如积分不足，sub-agent 可向老大发送审批请求：
```
「如音积分58分，执行敏感操作需审批
 操作：删除 /tmp/test.log
 [发送审批请求]」
```

老大回复后执行。

---

## 五、持续优化机制

> 说明：优化数据直接写在各 SKILL.md 的 frontmatter.metadata，巡检和更新均针对文件系统，无需独立索引文件。

### 5.1 使用后自动记录

```
skill 执行完毕
    │
    ▼
skill_index 工具：读取 SKILL.md frontmatter.metadata
    │
    ├── match_stats.total += 1
    ├── match_stats.true_positive += 1  或  false_positive += 1
    └── match_stats.last_used = now
    │
    ▼
patch SKILL.md frontmatter.metadata.match_stats
```

### 5.2 trigger_scenes 自动补全（新建/巡检时）

```
新建 skill 或 巡检发现 trigger_scenes = []
    │
    ▼
读取 SKILL.md 全文
    │
    ├── ## Usage / ## Trigger 章节 → 提取 trigger_scenes
    ├── ## Description / ## Purpose 章节 → 提取 keywords
    └── AI 语义补全（兜底）
    │
    ▼
自动追加到 frontmatter.metadata.trigger_scenes
    │
    ▼
patch SKILL.md
```

### 5.3 匹配质量反馈

```python
match_stats.total += 1

if 用户确认使用该 skill:
    match_stats.true_positive += 1
    match_rate = true_positive / total

if 用户拒绝该 skill 建议:
    match_stats.false_positive += 1

# match_rate < 0.6 持续 10 次
→ 标记为「低置信度」
```

### 5.4 inferred_triggers 推理补全

```
同类 skill 触发 ≥5 次
    │
    ▼
AI 分析：提取共同 pattern
    │
    ▼
追加到 inferred_triggers 列表
    │
    ▼
下次 L2 匹配时 inferred_triggers 参与中文匹配
```

### 5.5 手动干预

> 所有扩展字段直接编辑 SKILL.md，无需维护独立 JSON。

```
# 示例：手动补充 trigger_scenes
patch("SKILL.md",
  old_string="  trigger_scenes: []",
  new_string="  trigger_scenes:\n    - Bug排查\n    - 故障诊断")
```

---

## 六、心跳巡检机制（hermes-memory-maintenance）

> 变更说明（v2.1）：巡检直接扫描 SKILL.md 文件系统，无需维护独立索引文件。

### 6.1 巡检周期

每日 03:00 自动执行（hermes-memory-maintenance cronjob）

### 6.2 巡检内容

| 检查项 | 操作 |
|--------|------|
| 记忆库归档检查 | 检查是否有未归档内容 → 推送思月 |
| 新建 skill 检测 | rglob("~/.hermes/skills/**/SKILL.md") → 发现无 trigger_scenes → AI 补全 |
| trigger_scenes 缺失 | 发现 `metadata.trigger_scenes = []` → AI 提取并回填 |
| 休眠检测 | `last_used > 90天` → 标记 dormant |
| 异常条目清理 | 无（无独立 index，无需检查一致性） |
| 违规统计汇总 | 读取 bypass.log，生成周报 |
| sub-agent 积分计算 | 按规则计算各 sub-agent 积分 |

### 6.3 巡检逻辑

```
rglob("~/.hermes/skills/**/SKILL.md")
    │
    ▼
for skill_md in all_skill_files:
    │
    ├── frontmatter = parse(skill_md)
    ├── metadata = frontmatter.metadata
    │
    ├── metadata.trigger_scenes 为空？
    │     → AI 提取 → 回填 SKILL.md
    │
    ├── metadata.match_stats.last_used 超过 90 天？
    │     → 标记 dormant
    │
    └── metadata.owner 缺失？
          → 推断或留空待补
```

### 6.4 周报模板

```
═══════════════════════════════════════
Hermes Skill 索引巡检报告
时间：2026-04-30 03:00
═══════════════════════════════════════

【1. Skill 文件检查】
  • skills/ 目录总数：71
  • 新建 skill：0
  • trigger_scenes 待补全：3
    - github-auth（缺少触发场景）
    - blogwatcher（缺少触发场景）
    - godmode（缺少触发场景）

【2. 休眠 skill 检测】
  • 休眠（90天无触发）：2
    - godmode（最后使用：2026-01-15）
    - pokemon-player（最后使用：2026-02-20）

【3. sub-agent 积分状态】
  • 如音：92分（较上周 -1）
  • 紫灵：88分（较上周 +1）
  • 思月：95分（持平）

【4. 违规拦截统计】
  • 本周拦截次数：3次
  • 本月累计：7次
  • 趋势：↓ 较上月减少 2 次

【5. 异常告警】
  • 无

═══════════════════════════════════════
```

---

## 七、skill 分类体系（复用现有 category）

| Category | 职能定位 | 典型 skill |
|----------|----------|------------|
| `autonomous-ai-agents` | 多Agent协作、任务分发 | agent-delegate, multi-agent-delegate-workflow |
| `software-development` | 代码开发、调试、测试 | systematic-debugging, test-driven-development |
| `devops` | 部署、运维、CI/CD | webhook-subscriptions |
| `data-science` | 数据分析、Jupyter | jupyter-live-kernel |
| `mlops` | 模型训练、推理、部署 | llama-cpp, serving-llms-vllm |
| `github` | GitHub 相关工作流 | github-pr-workflow, github-code-review |
| `productivity` | 文档、演示、表格 | docs-commit-workflow, powerpoint |
| `note-taking` | Obsidian 笔记管理 | obsidian |
| `research` | 学术研究、信息检索 | arxiv, blogwatcher |
| `media` | 音视频、内容生成 | youtube-content, heartmula |
| `social-media` | 社交平台操作 | xurl |
| `smart-home` | 智能家居控制 | openhue |

#### 命名规范

- lowercase
- 用 hyphens `-` 分隔词（不用 underscores）
- 最大 64 字符
- 示例：`systematic-debugging`、`multi-agent-delegate-workflow`

---

## 八、owner 归属分配

| owner | 归属 | 说明 |
|-------|------|------|
| `xingruyin` | 如音专属 | 技术/实现类 skill |
| `ziling` | 紫灵专属 | 需求/创意类 skill |
| `wensiyue` | 思月专属 | 文档/归档类 skill |
| `shared` | 共享 | 跨职能通用 skill |

> **初始 owner 由银月手工补充，后续新建 skill 时自动按分类推断。**

---

## 九、已确认结论

- ✅ 公共配置（角色职责表等）大家只读，银月唯一写入
- ✅ 各 Agent 私有记忆写在自己目录，只读自己的，无冲突
- ✅ 全局 cronjob + 分散 cronjob 并存架构
- ✅ agent-delegate skill 路径已修正
- ✅ cronjob 触发时间：每天北京时间 03:00
- ✅ 日志记忆时间窗口：前日03:00 → 当日03:00（北京时间）
- ✅ 公共配置路径：`~/.hermes/profiles/shared/`，仅包含角色职责表（暂定单一文件）
- ✅ 同步范围议题删除：各 Agent 私有记忆不存在跨 Agent 同步需求
- ✅ 触发频率：每天
- ✅ OpenClaw 梦境机制：废弃，不再讨论
- ✅ 角色职责表：沿用文档7.7节现有分工表，公共配置文件统一为 `~/.hermes/profiles/shared/role-responsibility.md`
- ✅ 公共配置更新流程：废弃（角色职责表变更由银月直接覆盖文件，并通过飞书群通知各姐妹刷新记忆）
- ✅ **skill-index 方案 v2.1：Native Only + Metadata in SKILL.md**
  - 原 skill-index-ext.json 独立索引层方案废弃（token 效率不如 Native Only + 按需读取）
  - 所有优化数据（owner、trigger_scenes、match_stats、inferred_triggers）写入各 SKILL.md 的 frontmatter.metadata
  - manifest 只注入标准字段（name、description、category、tags），metadata 按需读取
  - 无独立索引文件，巡检直接扫描文件系统
  - 手动干预直接编辑 SKILL.md，无需维护两份数据
- ✅ 启动时加载 shared 配置：各姐妹启动时额外读取 `~/.hermes/profiles/shared/role-responsibility.md`

---

> 关联文档：[[多Agent记忆机制优化方案]] — 记忆机制主文档
> 关联文档：[[多Agent记忆机制优化实施方案]] — 待落地事项与实施框架
