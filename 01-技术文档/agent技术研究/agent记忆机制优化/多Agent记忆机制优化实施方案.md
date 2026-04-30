# 多Agent记忆机制优化实施方案

> 创建时间：2026-04-29
> 版本：v1.0
> 负责人：如音
> 用途：多Agent记忆机制优化的待落地事项与实施框架

---

## 一、落地清单

| # | 待落地事项 | 技术方向 | 状态 |
|---|-----------|---------|------|
| L1 | 初始化 skills-index.json | 扫描 `~/.hermes/skills/` 目录，提取每个 skill 的 name/path/category，生成 JSON 索引文件 | 待落地 |
| L2 | 手工补充 owner 归属 | 根据 skill 分类（技术/文档/需求）推断 owner，缺失的由银月手工指定 | 待落地 |
| L3 | ~~开发 skill-index skill~~ → MEMORY.md 索引摘要初始化 | 初始化时将 skills-index.json 关键字段（name/path/owner）同步到各姐妹 MEMORY.md 索引区；运行时按需查询，无需 skill | 待落地 |
| L4 | 实现硬拦截逻辑 | 在银月调用 skill 前增加 owner 校验，拦截非 shared skill 的直接调用 | 待落地 |
| L5 | 配置 hermes-memory-maintenance cronjob | 每日 09:00 执行，脚本扫描 skills-index/ 一致性、sub-agent 积分、bypass.log 统计 | 待落地 |
| L6 | 打通豁免审批流程（飞书消息） | 飞书发送审批消息，支持 [批准]/[拒绝] 按钮交互，超时自动处理 | 待落地 |

---

## 二、L1 实施框架：初始化 skills-index.json

```
步骤：
1. 扫描 ~/.hermes/skills/ 下所有 SKILL.md 文件
2. 提取文件名作为 skill name，目录结构作为 category
3. 读取 SKILL.md 头部 YAML/JSON 提取 trigger_scenes、keywords、purpose
4. 生成 skills-index.json 初稿（owner 暂填 shared）
5. 银月手工补充 owner 归属
```

**扫描命令示例**：
```bash
find ~/.hermes/skills/ -name "SKILL.md" -exec dirname {} \; | while read dir; do
  skill_name=$(basename "$dir")
  category=$(basename "$(dirname "$dir")")
  echo "{\"name\":\"$skill_name\",\"path\":\"$category/$skill_name\",\"owner\":\"shared\",\"category\":\"$category\"}"
done > ~/.hermes/skills-index/skills-index.json
```

---

## 三、L3 实施框架：MEMORY.md 索引摘要初始化

```
目标：打破 skill-index skill 与 skills-index.json 的循环依赖

实现方式：
- 初始化时扫描 ~/.hermes/skills/ 目录，读取各 SKILL.md 头部元数据
- 将 skills-index.json 关键字段（name/path/category/owner）同步到各姐妹 MEMORY.md 索引区
- 运行时直接查询 MEMORY.md 中的索引摘要，无需额外 skill
- skills-index.json 仅用于人工查阅和审计，不作为运行时依赖

索引摘要格式（写入各姐妹 MEMORY.md）：
```
| name | category | owner | 用途 |
|------|----------|-------|------|
| agent-delegate | autonomous-ai-agents | shared | 多Agent委托协作 |
| systematic-debugging | software-development | xingruyin | 系统性Bug排查 |
| obsidian | note-taking | wensiyue | Obsidian笔记管理 |
...
```

Token 消耗分析：
- 50 个 skills，索引约 3KB ≈ 750 tokens
- 启动时读一次，后续直接查，不重复消耗
```

---

## 四、L4 实施框架：硬拦截逻辑

```
实现位置：银月的 skill 调用入口（delegate_task 之前）
拦截条件：
  if skill.owner != "shared" and skill.owner != current_agent:
      拒绝调用，返回提示 + 豁免机制入口

豁免流程：
  - sub-agent 在线 → 飞书审批
  - sub-agent 离线 → 自动豁免（单次有效）
  - 豁免记录写入 bypass.log
```

---

## 五、L5 实施框架：hermes-memory-maintenance cronjob

```
触发时间：每日 09:00（北京时间）
执行内容：
  1. 扫描 skills/ 目录，与 skills-index.json 比对一致性
  2. 读取 bypass.log，统计拦截次数
  3. 计算各 sub-agent 积分
  4. 生成周报（每7天一次），推送飞书

巡检脚本位置：~/.hermes/scripts/memory-maintenance.sh
```

---

## 六、L6 实施框架：豁免审批流程

```
飞书审批消息格式：
「银月申请调用 [skill-name]
 原因：[银月填写]
 [批准] [拒绝] [5分钟后自动批准]」

技术实现：
  - 使用飞书 interactive card 消息
  - 按钮回调触发 approve/reject 逻辑
  - 超时由 cronjob 兜底处理
```

---

## 七、落地优先级

```
P0（必须，阻塞其他项）：L1 → L2
P1（核心机制）：L3 → L4
P2（配套功能）：L5 → L6
```

---

## 八、实施计划

| 阶段 | 行动 | 说明 |
|------|------|------|
| P0 | 各姐妹优化自己的 MEMORY.md | 按第五章模板精简，当前均已接近/超过 1200 字符 |
| P1 | 补充启动时读取日志流程 | 在 MEMORY.md 开头固化，或在 SOUL.md 中描述 |
| P2 | 创建巡检 Cron | 每个姐妹一条每日 21:00 巡检 |
| P3 | 测试任务交接日志 | 指定一个场景验证交接流程 |
| P4 | 验证启动时日志接续 | 重启某姐妹，验证是否读取日志 |

---

## 九、记忆管理原则

| 项目 | 说明 |
|------|------|
| 管理原则 | 各 Agent 自己管自己的记忆（MEMORY.md） |
| 审核机制 | 银月定期复核姐妹们的记忆 |
| 变更触发 | 任务结束后、角色被召唤时、大版本更新后 |

---

> 关联文档：[[多Agent记忆机制优化方案]] — 记忆机制主文档
> 关联文档：[[Skill管理机制]] — Skill索引体系与分工防护
