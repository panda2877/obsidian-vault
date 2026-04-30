# Skill管理机制

> 创建时间：2026-04-29
> 版本：v2.0
> 负责人：如音
> 用途：建立Skill索引体系、分工防护硬拦截、sub-agent信任积分机制
>
> 变更记录：
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

## 二、索引表设计

### 2.1 存储位置

```
~/.hermes/skills-index/
  ├── skills-index.json    # 底层索引（机器可读）
  └── skills-index.md      # 可读视图（人可读）
```

### 2.2 索引结构（skills-index.json）

```json
{
  "version": "2026-04-29",
  "skills": [
    {
      "name": "agent-delegate",
      "path": "autonomous-ai-agents/agent-delegate",
      "owner": "shared",
      "category": "autonomous-ai-agents",
      "purpose": "多Agent委托协作标准skill，银月用delegate_task召唤如音/紫灵/思月时使用",
      "trigger_scenes": ["召唤sub-agent", "任务分发", "多Agent协作"],
      "keywords": ["delegate", "spawn", "sub-agent", "召唤", "任务分发"],
      "dependencies": [],
      "last_updated": "2026-04-29"
    }
  ]
}
```

### 2.3 字段说明

| 字段 | 说明 |
|------|------|
| `name` | skill名称，唯一标识 |
| `path` | 相对于 skills 目录的路径 |
| `owner` | 归属：`xingruyin`（如音专属）、`ziling`（紫灵专属）、`wensiyue`（思月专属）、`shared`（共享） |
| `category` | 职能分类，复用现有 category 体系 |
| `purpose` | 一句话用途描述 |
| `trigger_scenes` | 触发场景列表（中文，便于匹配中文任务描述） |
| `keywords` | 关键词（中英文，用于语义匹配） |
| `dependencies` | 依赖的其他 skills |
| `last_updated` | 最后更新时间 |

### 2.4 索引调用机制（强制）

```
任务描述输入
    │
    ▼
skill-index skill 自动加载
    │
    ▼
读取 skills-index.json
    │
    ▼
三层匹配
  ├── L1：category 精确匹配
  ├── L2：trigger_scenes / keywords 关键词匹配
  └── L3：purpose + description 语义模糊匹配
    │
    ▼
返回推荐 skill（top 1-3），含 owner、匹配理由
    │
    ▼
owner = shared → 自行加载执行
owner = 如音/紫灵/思月 → delegate_task 委托执行
```

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

## 五、trigger_scenes 持续优化机制

### 5.1 智能补充策略

新建 skill 时，通过以下方式自动补充 trigger_scenes：

```
读取 SKILL.md 全文
    │
    ├── ## Usage / ## Trigger 章节 → 提取 trigger_scenes
    ├── ## Description / ## Purpose 章节 → 提取 keywords
    └── AI 语义补全（兜底）
```

### 5.2 使用后确认机制

```
skill 执行完毕
    │
    ▼
skill-index 自动记录
    │   ├── skill name
    │   ├── 任务描述（本次调用时的上下文）
    │   └── 调用时间戳
    │
    ▼
首次使用 → 强制确认提示
后续使用 → 可跳过
```

---

## 六、心跳巡检机制（hermes-memory-maintenance）

### 6.1 巡检周期

每日 09:00 自动执行

### 6.2 巡检内容

| 检查项 | 说明 |
|--------|------|
| 记忆库归档检查 | 检查是否有未归档内容 → 推送思月 |
| skill-index 一致性 | 检查 skills/ 目录与 skills-index.json 是否一致 |
| 缺失索引处理 | 发现新建 skill → 自动补充条目（trigger_scenes 留空待补） |
| 异常条目清理 | 发现已删除 skill → 移除索引条目 |
| 违规统计汇总 | 读取 bypass.log，生成周报 |
| sub-agent 积分计算 | 按规则计算各 sub-agent 积分 |

### 6.3 周报模板

```
═══════════════════════════════════════
Hermes Skill 索引巡检报告
时间：2026-04-29 周二 09:00
═══════════════════════════════════════

【1. 索引表一致性检查】
  • skills/ 目录总数：48
  • skills-index.json 条目数：48
  • 缺失索引：0
  • 异常条目：0
  • 状态：✅ 正常

【2. sub-agent 积分状态】
  • 如音：92分（较上周 -1）
  • 紫灵：88分（较上周 +1）
  • 思月：95分（持平）

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
- ✅ skill-index 不写成 skill，改为 MEMORY.md 索引摘要（启动时同步，运行时不扫描）
- ✅ 启动时加载 shared 配置：各姐妹启动时额外读取 `~/.hermes/profiles/shared/role-responsibility.md`

---

> 关联文档：[[多Agent记忆机制优化方案]] — 记忆机制主文档
> 关联文档：[[多Agent记忆机制优化实施方案]] — 待落地事项与实施框架
