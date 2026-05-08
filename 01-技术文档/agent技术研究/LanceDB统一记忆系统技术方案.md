# 基于 LanceDB 的统一记忆系统 — 技术设计文档

> 版本：v1.0
> 创建时间：2026-05-08
> 设计人：银月

---

## 一、设计目标

### 1.1 要解决的痛点

| # | 痛点 | 现状 | 目标 |
|---|------|------|------|
| P0 | **记忆管理混乱** | MEMORY.md/USER.md/SOUL.md 分散在多处，agent 自己都不知道读了什么，实际读取与反馈不一致 | **单库集中管理**，一套接口统一读写，读取链路透明可查 |
| P0 | **容量限制** | MEMORY.md 限 1800 字符，真正想记的塞不下，被迫精简取舍 | **无容量限制**，按需语义检索，只取相关的 3~5 条注入 |
| P0 | **共享记忆缺失** | 工具用法/环境配置等共用知识各姐妹各写一份，维护三份，改一个要同步改 | **shared 分类**，写一次所有 agent 共用 |
| P1 | **Token 消耗** | 每次对话全量注入 MEMORY/USER/SOUL ≈ 3700 字符 | 精简注入 ~700 字符 + 按需检索 3~5 条 |

### 1.2 核心原则

1. **一个 LanceDB 库，管所有记忆** — souls / user / shared / memories / sessions 全在一个库
2. **一套 HTTP API** — 读写、查询、浏览、管理，老大想看啥就看啥
3. **统一 USER** — 所有姐妹共用一份老大信息，不再各自维护
4. **读取链路透明** — 每次启动注入的记录都有日志，老大可随时查"我这次读了什么"

---

## 二、整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                   LanceDB 单库（~/.hermes/memory.lance）      │
│                                                             │
│  表名          │ 用途          │ 谁写入     │ 谁读取        │
│  ───────────── │ ──────────── │ ───────── │ ──────────── │
│  souls         │ 各姐妹人格设定 │ 各自写入   │ 各自必读      │
│  user          │ 老大信息      │ 银月维护   │ 所有姐妹必读   │
│  shared        │ 共用知识      │ 银月维护   │ 所有姐妹按需检索 │
│  memories      │ 专属经验记忆  │ 各自写入   │ 各自按需检索   │
│  sessions      │ 历史会话摘要  │ 各自写入   │ 不注入，手动查  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                           ↑
                          HTTP API（端口 9091）
                           ↑
    ┌───────┬───────┬───────┬───────┐
    │       │       │       │       │
   银月    如音    紫灵    思月    老大(管理)
```

### 2.1 启动读取流程（重构后）

```
对话启动
  │
  ├── 必读（注入 Prompt）
  │   ├── souls/{agent_name}     → 人格设定（~300字符）
  │   └── user/default          → 老大信息（~200字符，精简版）
  │
  ├── 语义检索（注入 Prompt）
  │   ├── shared/                → 按当前话题检索 TOP-3
  │   └── memories/{agent_name}  → 按当前话题检索 TOP-3
  │
  └── 不注入，仅手动查询
      └── sessions/{agent_name}  → 历史会话检索
```

**每次对话注入量**：~500 字符（必读） + ~600 字符（检索 5~6 条） ≈ **~1,100 字符**
**对比现在**：~3,700 字符 → **节省约 70% Token**

---

## 三、表结构设计

### 3.1 统一 Schema

所有表共用同一 schema，用 `category` + `owner` 区分：

```python
import pyarrow as pa

MEMORY_SCHEMA = pa.schema([
    pa.field('id', pa.string()),              # 唯一 ID：UUID 或 "soul:yinyue:001"
    pa.field('content', pa.string()),          # 记忆内容（纯文本）
    pa.field('category', pa.string()),         # 分类：soul / user / shared / memory / session
    pa.field('owner', pa.string()),            # 归属：yinyue / xingruyin / ziling / wensiyue / shared
    pa.field('vector', pa.list_(pa.float32(), 1536)),  # 向量嵌入
    pa.field('created_at', pa.int64()),        # 创建时间戳
    pa.field('updated_at', pa.int64()),        # 最后更新
    pa.field('tags', pa.list_(pa.string())),   # 标签，用于过滤
    pa.field('version', pa.int64()),           # 版本号，用于冲突检测
])
```

### 3.2 分类说明

#### souls 表

| 字段 | 示例值 |
|------|--------|
| id | `soul:yinyue:001` |
| content | 完整人格设定文本 |
| category | `soul` |
| owner | `yinyue` / `xingruyin` / `ziling` / `wensiyue` |
| tags | `[soul, personality, yinyue]` |
| **规则** | 每个 agent 1~3 条 soul 记录，启动时**按 owner 精确筛选 + 全部读取** |

#### user 表

| 字段 | 示例值 |
|------|--------|
| id | `user:default:001` |
| content | "老大从事项目管理，工作地深圳，时区北京。叫我银月/宝宝/宝贝/宝子..." |
| category | `user` |
| owner | `shared` |
| tags | `[user, profile]` |
| **规则** | **只有一份**，所有姐妹共用。按 `owner=shared AND category=user` 精确筛选读取 |

#### shared 表

| 字段 | 示例值 |
|------|--------|
| id | `shared:tool:lancedb` |
| content | "LanceDB 0.30.2 API 用法：lancedb.connect(uri) → create_table(schema) → add() → search()..." |
| category | `shared` |
| owner | `shared` |
| tags | `[tool, lancedb, database, vector]` |
| **规则** | 所有姐妹按语义检索，按 `owner=shared` 过滤 |

#### memories 表

| 字段 | 示例值 |
|------|--------|
| id | `memory:yinyue:20260508:001` |
| content | "老大对 Dashboard 节省内存的方案有不同意见——有开发就会反复起 Vite，不能靠静态化省内存" |
| category | `memory` |
| owner | `yinyue` |
| tags | `[preference, discussion]` |
| **规则** | 各姐妹按语义检索，按 `category=memory AND owner={self}` 过滤 |

#### sessions 表

| 字段 | 示例值 |
|------|--------|
| id | `session:yinyue:20260508` |
| content | LLM 总结的会话摘要 |
| category | `session` |
| owner | `yinyue` |
| tags | `[session, 20260508, memory-system]` |
| **规则** | **不注入 Prompt**，仅通过 HTTP API 或 search 手动查询 |

---

## 四、HTTP API 设计

### 4.1 基础信息

- **端口**：9091（独立于 Hermes Gateway 4000 和 todo-system 8080）
- **实现**：轻量 Python HTTP 服务（FastAPI 或自建 http.server）
- **认证**：本地绑定（127.0.0.1），仅内网访问

### 4.2 API 端点

#### 记忆读写

| 方法 | 路径 | 用途 |
|------|------|------|
| `GET` | `/api/v1/status` | 系统状态：库大小、各表条目数 |
| `POST` | `/api/v1/memories` | 写入一条记忆 |
| `GET` | `/api/v1/memories/{id}` | 按 ID 查询单条 |
| `PUT` | `/api/v1/memories/{id}` | 更新一条记忆 |
| `DELETE` | `/api/v1/memories/{id}` | 删除一条记忆 |
| `POST` | `/api/v1/search` | 语义检索（返回相关记忆列表） |

#### 查询与管理

| 方法 | 路径 | 用途 |
|------|------|------|
| `GET` | `/api/v1/memories?category=soul&owner=yinyue` | 按分类/归属查询 |
| `GET` | `/api/v1/memories?tag=tool` | 按标签查询 |
| `GET` | `/api/v1/injection/{agent_name}` | **查"某 agent 本次对话注入了什么"** |
| `GET` | `/api/v1/stats` | 统计：各 agent 记忆数、各分类占比 |

#### 管理

| 方法 | 路径 | 用途 |
|------|------|------|
| `POST` | `/api/v1/migrate/memory-to-shared` | 将某条记忆从专属移到共用 |
| `POST` | `/api/v1/migrate/shared-to-memory` | 将某条共用移到专属 |
| `GET` | `/api/v1/export` | 导出全库为 JSON |
| `POST` | `/api/v1/import` | 从 JSON 导入 |

### 4.3 API 使用示例

```bash
# 查银月当前注入了什么
curl http://localhost:9091/api/v1/injection/yinyue
# → {"injected": [
#     {"id":"soul:yinyue:001", "content":"银月的人格设定...", "source":"soul"},
#     {"id":"user:default:001", "content":"老大在深圳工作...", "source":"user"},
#     {"id":"shared:tool:lancedb", "content":"LanceDB用法...", "source":"shared", "relevance":0.92},
#     {"id":"memory:yinyue:...", "content":"老大对Dashboard的看法...", "source":"memory", "relevance":0.85}
# ]}

# 语义检索
curl -X POST http://localhost:9091/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query":"记忆系统怎么选型","owner":"yinyue","limit":5}'
# → {"results": [...]}

# 查 shared 里所有工具用法
curl "http://localhost:9091/api/v1/memories?category=shared&tag=tool"
# → {"count":12, "results":[...]}

# 统计
curl http://localhost:9091/api/v1/stats
# → {"total":245, "by_category":{"soul":4, "user":1, "shared":38, "memory":152, "session":50}}
```

---

## 五、共享记忆机制

### 5.1 谁可以写 shared

| 角色 | 写入权限 | 说明 |
|------|---------|------|
| **银月**（main-agent） | ✅ 可写 | 维护 shared 中所有内容 |
| **如音**（技术专家） | ✅ 可写 | 可写入技术类 shared 知识 |
| **紫灵**（需求专家） | ⚠️ 仅 shared:需求模板 | 只能写模板类内容 |
| **思月**（文档专家） | ⚠️ 仅 shared:文档规范 | 只能写规范类内容 |

### 5.2 shared 内容分类

```yaml
shared/:
  工具类:
    - lancedb 用法
    - sqlite-vss 用法
    - litellm 配置
    - hermes 命令速查
    - todo-system API
  环境类:
    - 服务器配置
    - 文件路径
    - 数据库连接
  约定类:
    - 代码规范
    - 文档规范
    - 命名规范
```

### 5.3 共享 vs 专属的判断标准

**放 shared 的**：工具用法、环境配置、代码规范、通用知识——"跟谁无关，学了就能用"
**放 memories 的**：对话中获得的经验教训、用户偏好、决策记录——"跟谁有关，是专属经历"

---

## 六、读取链路透明化（解决痛点 #1）

### 6.1 注入日志

每次对话启动时，系统自动记录：

```json
{
  "session_id": "conv_20260508_0918",
  "agent": "yinyue",
  "timestamp": 1746670680,
  "injected": [
    {"id": "soul:yinyue:001", "source": "必读", "length": 280},
    {"id": "user:default:001", "source": "必读", "length": 195},
    {"id": "shared:tool:lancedb", "source": "语义检索", "relevance": 0.92, "length": 320},
    {"id": "memory:yinyue:20260507:003", "source": "语义检索", "relevance": 0.85, "length": 180}
  ],
  "total_chars": 975
}
```

### 6.2 查询方式

```bash
# 查本次对话注入了什么
curl http://localhost:9091/api/v1/injection/yinyue

# 查历史注入记录
curl "http://localhost:9091/api/v1/injection/yinyue?history=true&limit=10"
```

### 6.3 对 agent 自身的影响

agent 在回复时如果被问到"你读了我什么信息"，可以：

> "老大，我这次读了你的个人信息、我的人格设定，还有 3 条相关记忆和 2 条工具知识。要不要我用 API 拉个清单给你看？"

---

## 七、迁移路径

### 阶段一：基础设施（1~2天）

1. 在 Hermes 环境安装 lancedb
2. 创建 `~/.hermes/memory.lance/` 库
3. 启动 HTTP API 服务（端口 9091）
4. 将现有 MEMORY.md / USER.md / SOUL.md 内容迁移到 LanceDB
5. 验证读写 + 检索功能

### 阶段二：读取链路替换（2~3天）

1. 修改 Hermes 启动流程：从 LanceDB 读取 souls + user，替代文件读取
2. 增加语义检索步骤：搜索 shared + memories，注入结果
3. 实现注入日志记录
4. 保留文件读取作为**降级方案**（API 不可用时回退）

### 阶段三：共享记忆构建（持续）

1. 将现有各姐妹的 SKILL.md 中的共用知识迁移到 shared 表
2. 清理重复内容
3. 建立 shared 维护规范

### 阶段四：session 接入（可选）

1. 对话结束后自动总结并写入 sessions 表
2. 替代现有的 session_search 功能（作为补充，非替代）

---

## 八、资源消耗评估

| 项目 | 增量 | 说明 |
|------|------|------|
| 磁盘 | **+50~200MB** | LanceDB 库文件，对 18GB 剩余完全可忽略 |
| 内存（API 服务） | **+30~50MB** | Python HTTP 服务，轻量 |
| 内存（LanceDB 运行时） | **~0** | LanceDB 是嵌入式库，内存随调用动态分配 |
| Embedding API 调用 | **按需** | 每次写入/检索调一次 MiniMax/OpenAI Embedding |
| **总内存增量** | **~30~50MB** | ✅ 在 500MB 余量内，安全 |
| Token 节省 | **~70%** | 从 3700 字符降到 ~1100 字符 |

---

## 九、风险与应对

| 风险 | 概率 | 影响 | 应对 |
|------|------|------|------|
| LanceDB 0.30.x API 不稳定 | 中 | 需适配 | 固定版本，升级前测试 |
| Embedding API 断网 | 低 | 无法写入/检索新记忆 | 降级为全量读入（保留文件读取作为 fallback） |
| 迁移过程中数据不一致 | 低 | 混乱 | 迁移期间双写（文件+LanceDB），确认稳定后切流 |
| HTTP API 成为单点故障 | 低 | 所有 agent 无法读写记忆 | 服务自启动 + systemd 托管 |

---

## 十、实施记录与踩坑经验

> 版本：v1.0 → v1.1（实施后更新）
> 实施时间：2026-05-08
> 实施人：幸如音

### 10.1 最终架构

```
LanceDB (memory.lance/) — 5 表，44 条记录
    │
    ├── systemd 服务托管 (lancedb-memory.service, 端口 9091)
    │   ├── 随服务器自启 (enabled)
    │   ├── Before=hermes-gateway.service (尽量先于 Hermes 启动)
    │   └── Restart=on-failure + RestartSec=5
    │
    ├── agent/lancedb_client.py (Hermes 侧 HTTP 客户端)
    │   ├── fetch_soul(agent_name) — LanceDB → 同步到 fallback SOUL.md
    │   ├── fetch_user()          — LanceDB → 同步到 fallback USER.md
    │   └── fetch_memories()      — LanceDB only，无文件 fallback
    │
    └── memory-service/main.py (API 服务)
        ├── POST/PUT → 自动同步 soul/user 到 fallback 文件
        └── hash embedding fallback (真实 API 按需接入)
```

### 10.2 文件 fallback 策略（最终版）

| 数据 | 主数据源 | fallback 文件 | 备注 |
|------|---------|--------------|------|
| **soul** (银月) | LanceDB | `/home/agentuser/.hermes/SOUL.md` | 银月专用 |
| **soul** (子 agent) | LanceDB | `/home/agentuser/.hermes/profiles/<name>/SOUL.md` | 各自 profile 下 |
| **user** | LanceDB | `/home/agentuser/.hermes/memories/USER.md` | **所有 agent 共用** |
| **memories** | **纯 LanceDB** | 无 | MEMORY.md 已全部清空 |

**写入同步机制**：通过 LanceDB API (POST/PUT) 写入 soul/user 时，服务端自动同步到对应的 fallback 文件。读取时如果 LanceDB 可用，同步覆盖文件；如果不可用，从文件读取。

### 10.3 实施踩坑记录

#### 🕳️ 坑 1：LanceDB DELETE 按 id 匹配会删掉所有同名记录

LanceDB 的 `delete(id)` 是按主键匹配，如果多个记录有相同 id 格式前缀（如 `soul:xingruyin:001`），DELETE 会删掉所有匹配的记录。

**解决方案**：使用带后缀的 ID 格式（如 `soul:xingruyin:v1`），避免误删。或者在迁移时确保 ID 唯一。

```python
# ✅ 正确
"soul:xingruyin:v1"
# ❌ 错误（会被 delete 误伤同名记录）
"soul:xingruyin:001"
```

#### 🕳️ 坑 2：systemd 环境下的 HOME 与虚拟环境不一致

Hermes 的 `HERMES_HOME` 指向 `profiles/<name>` 目录（如 `/home/agentuser/.hermes/profiles/xingruyin`），导致 `~` 在 Hermes 环境和 systemd 环境下解析不同。

- Hermes 环境：`~/.hermes/memory.lance` → `/home/agentuser/.hermes/profiles/xingruyin/home/.hermes/memory.lance`
- systemd 环境：`~/.hermes/memory.lance` → `/home/agentuser/.hermes/memory.lance`

**解决方案**：建 symlink 统一路径
```bash
ln -s /home/agentuser/.hermes/profiles/xingruyin/home/.hermes/memory.lance \
      /home/agentuser/.hermes/memory.lance
```

#### 🕳️ 坑 3：httpx 依赖导致 systemd 启动失败

`embedding.py` 在模块级别 `import httpx`，但 systemd 环境下虚拟环境中未安装 httpx。

**解决方案**：改为 lazy import——只有在实际调用真实 embedding API 时才 import httpx，默认 hash fallback 不需要。

```python
# embedding.py 中
class EmbeddingProvider:
    async def _get_client(self):
        if self._client is None:
            import httpx  # lazy import
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client
```

#### 🕳️ 坑 4：服务器重启后 LanceDB 未自动拉起导致 Hermes 先启动

没有 systemd 服务托管时，服务器重启后 LanceDB 不会自动启动，Hermes 先启动时连不上 LanceDB。

**解决方案**：双保险
1. **systemd 启动顺序**：`lancedb-memory.service` 设 `Before=hermes-gateway.service`
2. **客户端重试**：`lancedb_client.py` 中 `_api_get()` 首次调用最多重试 5 次（共 10s），后续调用 fail fast

```python
_had_successful_call = False  # 模块级标记

def _api_get(path):
    max_attempts = 1 if _had_successful_call else 5  # 首次重试
    for attempt in range(1, max_attempts + 1):
        try:
            resp = urllib.request.urlopen(url, timeout=5)
            _had_successful_call = True
            return json.loads(resp.read())
        except Exception as e:
            if attempt < max_attempts:
                time.sleep(2)  # 等待 2s 后重试
            else:
                return None  # 最终失败，走 fallback
```

#### 🕳️ 坑 5：get_hermes_home() 路径层级判断错误

`get_hermes_home()` 返回 `profiles/<agent_name>`，`h.parent.name` 是 `profiles` 而非 agent 名。应使用 `h.name` 获取 agent 名称。

```python
# ✅ 正确
_home = get_hermes_home()  # /home/agentuser/.hermes/profiles/xingruyin
_profile_name = _home.name  # "xingruyin" ✅

# ❌ 错误
_profile_name = _home.parent.name  # "profiles" ❌
```

#### 🕳️ 坑 6：子 agent soul 同步覆盖银月 SOUL.md

LanceDB 读取 soul 成功后，`fetch_soul()` 中直接同步到全局 `FALLBACK_SOUL_PATH`，导致子 agent（如如音）的 soul 覆盖了银月的 `SOUL.md`。

**解决方案**：按 agent 类型决定 fallback 路径
- 银月 (hermes/home) → `/home/agentuser/.hermes/SOUL.md`
- 子 agent (xingruyin/ziling/wensiyue) → `/home/agentuser/.hermes/profiles/<name>/SOUL.md`

### 10.4 关键文件清单

| 文件 | 用途 |
|------|------|
| `~/.hermes/hermes-agent/agent/lancedb_client.py` | Hermes 侧 HTTP 客户端（读取 + 文件同步） |
| `~/.hermes/hermes-agent/agent/prompt_builder.py` | `load_soul_md()` 改由 LanceDB 读取 |
| `~/.hermes/hermes-agent/tools/memory_tool.py` | `MemoryStore.load_from_disk()` 改由 LanceDB 读取 |
| `~/.hermes/memory-service/main.py` | FastAPI 服务 + 文件同步钩子 |
| `~/.hermes/memory-service/lancedb_client.py` | LanceDB CRUD 封装 |
| `~/.hermes/memory-service/embedding.py` | 嵌入提供者（hash fallback，httpx lazy import） |
| `~/.hermes/memory-service/migrate_all.py` | 全量数据迁移脚本 |
| `/etc/systemd/system/lancedb-memory.service` | systemd 服务单元 |
| `~/.hermes/memory.lance → profiles/xingruyin/home/.hermes/memory.lance` | 数据库 symlink |

### 10.5 后续待办

- [ ] **接入真实 Embedding**：配置 MiniMax/OpenAI API key 替换 hash fallback
- [ ] **阶段三：shared 记忆构建**：将 SKILL.md 中的共用知识迁移到 shared 表
- [ ] **阶段四：session 接入**：对话自动总结写入 sessions 表
- [ ] **银月 soul 写入 LanceDB**：目前银月无 soul 在 LanceDB，读取时走 fallback 文件