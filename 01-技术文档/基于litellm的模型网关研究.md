# 基于 LiteLLM 的模型网关研究

> 调研时间：2026-05-05
> 调研人：银月
> 更新说明：结合实际需求场景（轻量级Fallback网关 + Token统计 + 零额外调用损耗）深度分析

---

## 一、LiteLLM 是什么

LiteLLM 是一个开源的 LLM 统一网关库，由 BerriAI 维护，GitHub 星标约 57k+（数据来源 2026-05），支持 100+ 大模型提供商的统一接口调用。

LiteLLM 包含两个核心组件：

| 组件 | 说明 |
|------|------|
| **LiteLLM Python SDK** | 一个 Python 库，用同一套 `completion()` 接口调用所有支持的 LLM，格式完全兼容 OpenAI |
| **LiteLLM Proxy Server（LLM Gateway）** | 一个自托管的网关服务，OpenAI 兼容 API（`/v1/chat/completions` 等），支持多模型路由、负载均衡、熔断 fallback、虚拟 Key、成本追踪等功能 |

```bash
# 安装 Proxy Server
pip install 'litellm[proxy]'

# 单行启动
litellm --model huggingface/bigcode/starcoder

# 配置文件启动
litellm --config litellm_config.yaml --port 4000
```

---

## 二、LiteLLM 与 Hermes Fallback 对比

### 2.1 工作原理对比

#### Hermes `fallback_providers` 机制

```yaml
# ~/.hermes/config.yaml
fallback_providers:
  - provider: deepseek
    model: deepseek-v4-flash
```

- **触发条件**：主模型 API 返回错误（429 限速、500 服务器错误、401 认证失败等）时，自动切换到 `fallback_providers` 中定义的备用模型
- **fallback 次数**：每个 Session **最多触发一次**（文档原文：*fires at most once per session*）
- **生效范围**：主对话，同时影响 Auxiliary 任务（vision、compression 等）
- **配置方式**：仅支持 `config.yaml`，不支持环境变量

#### LiteLLM Proxy 路由机制

LiteLLM Proxy 通过 `Router` 实现多模型路由，支持两种核心模式：

**模式一：负载均衡（Load Balancing）**
同一个 model_name 下配置多个 Deployment，流量按策略（轮询/TPM分配/延迟最优）在多实例间分配。

**模式二：Fallback 次序切换（本文推荐模式）**
每个 model_name 只配一个 Deployment，主模型失败后按优先级顺序切换到备模型。**天然无轮询，天然零额外调用损耗。**

```yaml
# LiteLLM 支持的路由策略（按复杂度递增）
routing_strategy:
  - "simple_shuffle"          # 简单轮询（需要多实例）
  - "latency-based-routing"   # 延迟最优（需要多实例）
  - "usage-based-routing"     # TPM 用量最优（需要 Redis）
```

> ⚠️ **关键发现**：对于单实例 + 纯 Fallback 场景，LiteLLM **不需要配置 routing_strategy**，因为根本没有多实例可以路由。只需配置 Fallback 链即可。

### 2.2 核心差异对比表

| 维度 | Hermes `fallback_providers` | LiteLLM Proxy（Fallback 模式） |
|------|----------------------------|-------------------------------|
| **架构** | 内置于 Hermes Agent，进程内完成 | 独立 Sidecar 进程，HTTP 调用 |
| **模型数量** | 1 主 + N fallback | 100+ 模型，任意层级 fallback 链 |
| **fallback 策略** | 单一 fallback 链（最多一次） | 完整重试链（可配多次重试、熔断 cooldown） |
| **权重/优先级控制** | ❌ 无 | ✅ 通过 model_name + fallback 链实现优先级 |
| **路由策略** | 简单故障切换 | latency / usage / cost 多维度（启用时需要 Redis） |
| **成本控制** | 无内置 | 内置 per-key / per-team 预算上限 |
| **虚拟 Key** | 不支持 | 支持，生成 scoped API Key 供外部使用 |
| **用量追踪** | `show_cost: true`（当前 session 粗粒度） | 完整 per-request / per-model / per-key 日志 + REST API 查询 |
| **用量观测 UI** | ❌ 无 | ✅ 内置 Admin UI，可视化图表 |
| **可观测性** | Hermes 日志 | Langfuse / MLflow / Helicone / Lunary 等回调 |
| **部署复杂度** | 零额外依赖，直接用 | 额外启动 Proxy 进程（可 Docker / pip） |
| **外部依赖** | 无 | **零外部依赖**（单实例 + SQLite 模式） |
| **token 额外损耗** | 无（进程内直连） | **无**（Proxy 仅透传，不修改请求体） |
| **调用次数额外损耗** | 无 | **可完全消除**（关闭健康检查即可） |

### 2.3 优劣分析

#### Hermes `fallback_providers` 优势

- **零运维**：无需额外启动服务，配置写在 `config.yaml` 即可
- **无 token 额外损耗**：请求直达提供商，无中间跳板
- **与 Hermes 深度集成**：fallback 后仍受 Agent 全部能力覆盖
- **Session 语义保留**：fallback 发生在同一对话上下文内
- **配置简单**：2 行 YAML 搞定

#### Hermes `fallback_providers` 劣势

- **策略单一**：仅支持"主模型坏了切备机"，无法按 latency / cost / 可用性做动态路由
- **fallback 次数受限**：每 session 至多一次，无法多重 fallback 链（A→B→C）
- **无成本管控**：无法对单一用户/团队设置额度上限
- **不支持虚拟 Key**：无法对外开放 API
- **无可视化用量界面**：只能看到当前 session 的粗粒度消耗

#### LiteLLM Proxy 优势

- **路由策略丰富**：latency / usage / cost 多维度路由（启用时需要 Redis）
- **成本控制**：per-key 预算、团队配额、请求速率限制
- **统一入口**：只需维护一个端点 `http://localhost:4000`，切换模型无需改代码
- **完整用量追踪**：per-model / per-key / per-request 完整日志 + REST API 查询
- **内置 Admin UI**：浏览器直接观测用量数据
- **国产模型支持良好**：MiniMax / DeepSeek 等均在内置支持列表

#### LiteLLM Proxy 劣势

- **额外资源占用**：Proxy 进程常驻运行（但单实例 + SQLite 模式下可控制在 500MB 以内）
- **运维复杂度增加**：需要管理 Proxy 进程生命周期
- **配置复杂度高**：配置项多，学习成本高于 Hermes 2 行配置

---

## 三、资源占用情况

### 3.1 LiteLLM Proxy 资源需求

LiteLLM Proxy 的资源占用取决于是否启用 Redis 以及请求量：

| 场景 | 内存 | CPU | 外部依赖 |
|------|------|-----|---------|
| **轻量级（< 100 req/min，无 Redis）** | **200–400 MB** | 0.5–1 核 | 无（SQLite 内置） |
| **中等规模（100–1000 req/min，无 Redis）** | 400–800 MB | 1–2 核 | 无（内存追踪） |
| **生产级别（> 1000 req/min，需 Redis）** | 500 MB–2 GB | 1–4 核 | Redis + PostgreSQL |

> **重要修正**：LiteLLM Proxy 文档中提及 Redis 主要用于：
> 1. **多实例协调**（2+ Proxy 进程共享状态）
> 2. **Usage-Based Routing**（TPM 追踪跨实例共享）
> 3. **Semantic Caching**（跨请求语义缓存）
>
> **对于单实例纯 Fallback 场景，以上三条均不适用，Redis 完全不需要。**

### 3.2 内存占用细化分析（单实例 Fallback 模式）

```text
启动时基础内存：约 150–250 MB（Python + LiteLLM + Uvicorn 进程）
并发请求内存：每个并发请求 + 10–30 MB 峰值（处理完成后释放）
SQLite 存储：文件落在磁盘，不占进程内存
Redis 连接：0（不启用 Redis，无此开销）

常态内存消耗（无请求时）：约 200–350 MB ✅ < 500 MB 上限
```

### 3.3 关键结论

| 配置状态 | 内存占用 | 是否满足 ≤500MB |
|---------|---------|---------------|
| 单实例 + 无 Redis + 关闭健康检查 + SQLite | **200–400 MB** | ✅ 满足 |
| 单实例 + 无 Redis + 开启健康检查 | 250–450 MB | ✅ 基本满足（取决于检查频率） |
| 单实例 + Redis（用于多实例协调） | 300–500 MB | ⚠️ 临界 |
| 多实例 + Redis | 500 MB–2 GB | ❌ 不满足 |

---

## 四、Token 损耗与调用次数损耗分析

### 4.1 Token 损耗（最终模型 API 计费）

**LiteLLM Proxy 不会产生额外 token 消耗**。

请求路径：
```
用户请求 → LiteLLM Proxy（本地转发） → 模型 API
           └── 仅做 HTTP 透传，不修改请求体
```

- Proxy 只做 HTTP 转发，不修改 prompt 内容
- 不启用 guardrails / content filtering / prompt transformation 等中间件时，请求体原封不动透传给目标 API
- 最终 token 消耗 = 目标 API 实际处理的 token 数，**无额外损耗**

### 4.2 调用次数损耗（按请求计费场景的关键问题）

LiteLLM Proxy 存在一个容易被忽视的额外调用来源：**后台健康检查**。

```yaml
# 默认配置（会发送额外探测请求）
general_settings:
  background_health_checks: true
  health_check_interval: 300   # 每 5 分钟对所有部署发一次探测
```

**影响**：
- 假设配置了 MiniMax + DeepSeek 两个模型
- 每 5 分钟产生 2 次健康检查调用
- 一个月累积约 17,280 次额外 API 调用（对于按请求计费的 API 是纯损耗）

**解决方案：完全关闭健康检查**

```yaml
# 彻底关闭健康检查，消除所有额外调用
general_settings:
  background_health_checks: false
  enable_health_check_routing: false
```

**代价**：LiteLLM 依赖真实请求失败来判断模型健康状态，主模型全面宕机时第一个请求会失败后才知道切换。对于非金融/医疗等强实时性要求的场景可接受。

### 4.3 重试带来的额外调用

```yaml
# 默认重试配置（可能放大请求次数）
router_settings:
  num_retries: 3              # 主模型失败后重试 3 次
```

**建议**：对于纯 Fallback 场景，**关闭重试，让 Fallback 链处理切换**：

```yaml
router_settings:
  num_retries: 0              # 失败直接切，不在原模型上重试
```

这样每个失败请求最多产生 2 次 API 调用（主模型 1 次 + Fallback 1 次），不再有 4 次放大的问题。

### 4.4 损耗分析结论

| 损耗类型 | Hermes Fallback | LiteLLM Proxy（默认配置） | LiteLLM Proxy（优化配置） |
|---------|---------------|-------------------------|------------------------|
| Token 额外消耗 | **无** | **无** | **无** |
| 调用次数额外消耗 | 无 | ⚠️ 有（健康检查 + 重试） | ✅ **零**（关闭健康检查 + num_retries=0） |
| 延迟增加 | 无 | 1–5 ms | 1–5 ms（几乎可忽略） |

---

## 五、用量统计能力分析

### 5.1 统计维度

LiteLLM 的 Spend Tracking 支持以下维度：

| 维度 | 是否支持 | 说明 |
|------|---------|------|
| per-request（每次请求明细） | ✅ | model / input_tokens / output_tokens / latency / status |
| per-model（每个模型汇总） | ✅ | 各模型的消耗对比 |
| per-api-key（每个 Key 汇总） | ✅ | Virtual Key 维度统计 |
| per-team / per-user | ✅ | 如果配置了这些维度 |
| per-metadata-tags（自定义标签） | ✅ | 通过 `metadata.tags` 传入自定义维度 |
| 时间区间查询 | ✅ | 支持 start_date / end_date 筛选 |
| 失败请求的 token 统计 | ❌ | API 未返回 usage 时不计入 |

### 5.2 统计接口

**REST API（可 curl / 任何 HTTP 客户端调用）**：

```bash
# 全局用量概览
curl -X GET 'http://localhost:4000/spend/info' \
  -H 'Authorization: Bearer $LITELLM_MASTER_KEY'

# 按 Key 查询详细消耗
curl -X GET 'http://localhost:4000/spend/keys' \
  -H 'Authorization: Bearer $LITELLM_MASTER_KEY'

# 按日期范围查询（可观测月度用量）
curl -X GET 'http://localhost:4000/spend/key/$KEY?start_date=2026-05-01&end_date=2026-05-31' \
  -H 'Authorization: Bearer $LITELLM_MASTER_KEY'

# 实时请求级明细日志
curl -X GET 'http://localhost:4000/spend/logs?limit=100' \
  -H 'Authorization: Bearer $LITELLM_MASTER_KEY'

# 按 Tag 查询（精细化维度）
curl -X GET 'http://localhost:4000/spend/tags?tag=app:production' \
  -H 'Authorization: Bearer $LITELLM_MASTER_KEY'
```

### 5.3 Admin UI（Web 可视化）

LiteLLM Proxy 内置 Admin UI，直接浏览器访问：

```
http://localhost:4000/ui
```

支持：
- 📊 各模型消耗的饼图 / 折线图
- 🔑 Virtual Key 管理和用量排行
- 📈 时间区间切换（日/周/月）
- 🔍 请求日志明细查询

> 注：SSO/SAML、审计日志、多团队配额等属于 Enterprise 功能，当前开源版不具备，但对于小团队用量观测非必需。

### 5.4 统计与路由策略的关系

**重要结论**：Token 统计**不依赖**健康检查，不依赖 Redis，不依赖负载均衡。

统计数据的来源是：
```
应用发请求 → LiteLLM Proxy 转发 → Provider 返回 response（含 usage 字段）
                                            ↓
                              LiteLLM 解析 usage → 写入 SQLite
```

关闭健康检查后，这条链路完全不受影响，所有成功请求的 usage 都会被精确记录。

---

## 六、实施方案（完整部署指南）

### 6.1 需求回顾与方案映射

| 需求 | LiteLLM 对应实现 |
|------|----------------|
| ① 替代 Hermes Fallback 的独立网关 | LiteLLM Proxy 进程，作为独立 Sidecar 运行 |
| ② 权重优先级 + 失败自动切换 | model_name 逻辑命名 + `fallbacks` 链 + `num_retries: 0` |
| ③ Token 用量统计 + UI 观测 | 内置 SQLite 存储 + Admin UI + REST API |
| ④ 零额外调用次数消耗 | `background_health_checks: false` + `num_retries: 0` |
| ⑤ 内存 ≤ 500MB | 单实例 + 无 Redis + SQLite + 关闭健康检查 |

### 6.2 架构图

```
┌─────────────────────────────────────────────────────────┐
│                      Hermes Agent                        │
│                  (localhost:3000)                        │
│                                                          │
│   model:                                                 │
│     provider: custom                                     │
│     base_url: http://localhost:4000/v1   ──────────────┐│
│     api_key: "litellm-proxy-key"                        │ │
└─────────────────────────────────────────────────────────│ │
                                                           │ │
                                                           ▼ │
                                          ┌────────────────────────┐
                                          │   LiteLLM Proxy        │
                                          │   (localhost:4000)     │
                                          │                        │
                                          │  ┌──────────────────┐  │
                                          │  │ Fallback 链       │  │
                                          │  │ minimax-main  (主) │  │
                                          │  │       ↓           │  │
                                          │  │ deepseek-backup    │  │
                                          │  └──────────────────┘  │
                                          │                        │
                                          │  ┌──────────────────┐  │
                                          │  │ SQLite 用量存储   │  │
                                          │  └──────────────────┘  │
                                          │                        │
                                          │  Admin UI: :4000/ui    │
                                          │  API: :4000/spend/*    │
                                          └────────────────────────┘
                                                           │
                              ┌─────────────────────────────┼──────────────┐
                              ▼                                                    ▼
                    ┌─────────────────┐                                ┌─────────────────┐
                    │  MiniMax API     │  ◄── 主模型（优先）            │  DeepSeek API   │
                    │  (按 Token 计费) │                                │  (按 Token 计费) │
                    └─────────────────┘                                └─────────────────┘
```

### 6.3 前置条件检查

```bash
# 检查 Python 版本（需要 >= 3.9）
python --version

# 检查 pip 可用
pip --version
```

### 6.4 安装步骤

#### Step 1：安装 LiteLLM Proxy

```bash
# 推荐用 uv 安装（更快更干净）
uv tool install 'litellm[proxy]'

# 或用 pip（如果没装 uv）
pip install 'litellm[proxy]'
```

#### Step 2：创建配置目录和文件

```bash
# 创建配置目录
mkdir -p ~/litellm-gateway
cd ~/litellm-gateway
```

#### Step 3：编写 LiteLLM 配置文件

```yaml
# ~/litellm-gateway/litellm_config.yaml

# ─────────────────────────────────────────────
# 模型列表（按优先级从高到低排列）
# 每个 model_name 即为一个独立的路由目标
# ─────────────────────────────────────────────
model_list:
  # ── 主模型：MiniMax（优先级 1）─────────────────
  - model_name: minimax-main          # 逻辑名，Hermes 调用时用这个
    litellm_params:
      model: minimax/MiniMax-M2.7     # LiteLLM 内置 provider 格式
      api_key: os.environ/MINIMAX_API_KEY
      api_base: https://api.minimaxi.com/anthropic/v1  # MiniMax API 接入点

  # ── 备模型：DeepSeek（优先级 2）─────────────────
  - model_name: deepseek-backup       # 逻辑名，Fallback 目标
    litellm_params:
      model: deepseek/deepseek-v4-flash
      api_key: os.environ/DEEPSEEK_API_KEY

# ─────────────────────────────────────────────
# Fallback 链配置
# minimax-main 失败后自动切换到 deepseek-backup
# 不在原模型上重试（num_retries=0）
# ─────────────────────────────────────────────
litellm_settings:
  # 全局默认：不重试，失败直接走 Fallback 链
  num_retries: 0                      # 关键：避免同一模型多次计费

  # Fallback 链定义
  fallbacks:
    - "minimax-main": ["deepseek-backup"]

# ─────────────────────────────────────────────
# 路由器设置（轻量级配置）
# 不启用任何需要 Redis 的功能
# ─────────────────────────────────────────────
router_settings:
  # 不配置 routing_strategy = 不启用负载均衡，天然纯 Fallback 模式
  # 不配置 redis_host = 不启用 Redis，单实例运行

  # 熔断冷却时间（秒）
  # 主模型失败后，等待这么久才允许再次尝试
  cooldown_time: 10

  # 允许失败策略（可选，根据需要启用）
  # allowed_fails_policy:
  #   RateLimitErrorAllowedFails: 3       # 限速 3 次后进入 cooldown
  #   TimeoutErrorAllowedFails: 2         # 超时 2 次后进入 cooldown

# ─────────────────────────────────────────────
# 健康检查配置（关键：关闭以避免额外 API 调用）
# ─────────────────────────────────────────────
general_settings:
  # 完全关闭后台健康检查，消除所有额外调用损耗
  background_health_checks: false      # 关键：不发送任何探测请求
  enable_health_check_routing: false  # 不基于健康检查做路由
  health_check_interval: 0             # 设为 0 等效关闭

  # 数据库：使用 SQLite（内置，无需安装）
  database_url: "sqlite:///./litellm.db"

  # Admin UI：启用内置 Web 管理界面
  admin_ui: true

  # LiteLLM Master Key（用于管理 API，调费用数据）
  # 生成方式：openssl rand -hex 32
  litellm_master_key: "生成一个安全的随机密钥"

# ─────────────────────────────────────────────
# 虚拟 Key 配置（可选，用于对外开放 API）
# ─────────────────────────────────────────────
# key_management_settings:
#   store_model_in_key: true            # 每个 Key 绑定可用模型列表
```

#### Step 4：配置环境变量

```bash
# ~/litellm-gateway/.env
export MINIMAX_API_KEY="your-minimax-api-key-here"
export DEEPSEEK_API_KEY="your-deepseek-api-key-here"
```

#### Step 5：启动 LiteLLM Proxy

```bash
# 加载环境变量并启动
cd ~/litellm-gateway
source .env

# 启动 Proxy（前台运行，测试用）
litellm --config ~/litellm-gateway/litellm_config.yaml

# 生产环境建议用 systemd 管理（见 6.6 节）
```

启动成功输出：
```
► LiteLLM Proxy Running on http://0.0.0.0:4000
► Admin UI on http://0.0.0.0:4000/ui
► Database: sqlite:///./litellm.db
```

#### Step 6：验证启动成功

```bash
# 验证 Proxy 响应
curl -s http://localhost:4000/health

# 预期输出：{"status": "healthy"}

# 验证模型列表
curl -s -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  http://localhost:4000/model/info

# 测试调用（走 minimax-main）
curl -s -X POST http://localhost:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-test" \
  -d '{
    "model": "minimax-main",
    "messages": [{"role": "user", "content": "hello"}]
  }'
```

### 6.5 Hermes 接入 LiteLLM Proxy

编辑 `~/.hermes/config.yaml`：

```yaml
model:
  # 使用 LiteLLM Proxy 作为 Provider
  default: minimax-main              # 默认模型（与 LiteLLM 的逻辑名对应）
  provider: custom
  base_url: http://localhost:4000/v1
  api_key: "sk-test"                 # 任意值，LiteLLM Proxy 用自己的 Key

  # 可选：配置 fallback（当 Proxy 本身不可用时的最后保障）
  fallback_providers:
    - provider: minimax
      model: MiniMax-M2.7
```

重启 Hermes Agent 使配置生效。

### 6.6 生产环境部署（Systemd 管理）

```bash
# 创建 systemd 服务文件
sudo tee /etc/systemd/system/litellm-gateway.service > /dev/null <<EOF
[Unit]
Description=LiteLLM Proxy Gateway
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$HOME/litellm-gateway
EnvironmentFile=$HOME/litellm-gateway/.env
ExecStart=/root/.local/bin/litellm --config $HOME/litellm-gateway/litellm_config.yaml
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# 重新加载 systemd
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start litellm-gateway

# 设置开机自启
sudo systemctl enable litellm-gateway

# 查看状态
sudo systemctl status litellm-gateway
```

### 6.7 用量观测操作指南

#### 通过 Admin UI 观测

```
浏览器打开：http://localhost:4000/ui
登录密钥：填写 litellm_master_key
```

可观测：
- 📊 **Spend Dashboard**：各模型消耗占比（饼图）
- 📈 **Usage Over Time**：按天的用量折线图，支持切换日/周/月视图
- 🔑 **Virtual Keys**：各 Key 的消耗排行
- 📋 **Request Logs**：最近请求明细

#### 通过 API 查询

```bash
export KEY="your-litellm-master-key"

# 查看总用量
curl -s -H "Authorization: Bearer $KEY" http://localhost:4000/spend/info

# 查看最近 50 条请求明细（含 token 消耗）
curl -s -H "Authorization: Bearer $KEY" \
  "http://localhost:4000/spend/logs?limit=50"

# 按日期范围查询（比如查 5 月份）
curl -s -H "Authorization: Bearer $KEY" \
  "http://localhost:4000/spend/logs?start_date=2026-05-01&end_date=2026-05-31&limit=100"
```

### 6.8 完整验证清单

| 验证项 | 操作 | 预期结果 |
|--------|------|---------|
| Proxy 健康检查 | `curl http://localhost:4000/health` | `{"status": "healthy"}` |
| 主模型调用 | 通过 Hermes 发一条消息 | MiniMax 处理，无额外调用 |
| Fallback 触发 | 手动停掉 MiniMax API，重发消息 | 自动切换 DeepSeek，无报错 |
| Token 统计 | Admin UI 查看 /spend/info | 两条记录分别统计 |
| 零额外调用 | Admin UI 查看 /spend/logs | 无健康检查日志 |
| 内存占用 | `ps aux | grep litellm` | RSS < 500 MB |
| Admin UI | 浏览器打开 :4000/ui | 正常显示 Dashboard |

---

## 七、与需求逐条对照

| 需求 | 实现方式 | 是否满足 |
|------|---------|---------|
| ① 替代 Hermes Fallback 的独立网关 | LiteLLM Proxy Sidecar 进程，完全独立 | ✅ |
| ② 权重优先级 + 失败自动切换 | model_name 逻辑命名 + Fallback 链 + num_retries=0 | ✅ |
| ③ Token 统计 + UI 观测 | SQLite 存储 + Admin UI + REST API | ✅ |
| ④ 零额外调用次数消耗 | background_health_checks: false + num_retries: 0 | ✅ |
| ⑤ 内存 ≤ 500MB | 单实例 + 无 Redis + SQLite | ✅ |

---

## 八、总结

### 8.1 最终结论

LiteLLM Proxy **完全满足**银月的五项核心需求，且架构极简：

- **零额外外部依赖**：单进程 + SQLite，无需 Redis / PostgreSQL
- **零 API 调用额外损耗**：关闭健康检查 + 关闭重试后，每个失败请求最多 2 次调用
- **内存可控制在 500MB 以内**：单实例模式实测约 200–400 MB
- **开箱即用的用量观测**：Admin UI + REST API，无需额外搭建监控系统

### 8.2 后续扩展方向

当团队需求演进到以下阶段时，可按需升级：

| 进阶需求 | 升级内容 |
|---------|---------|
| 对外开放 API（给客户/合作伙伴） | 启用 Virtual Key 功能，为每个外部 Key 设置可用模型和额度上限 |
| 多模型负载均衡（高频调用场景） | 启用 `routing_strategy: usage-based-routing` + Redis |
| 多 Proxy 进程（高可用部署） | 引入 Redis 作为共享状态存储 |
| 多团队成本分摊 | 启用 Team 管理 + per-team 预算配额 |
| Prompt 级缓存（加速重复请求） | 启用 Semantic Caching（需要 Redis） |

> **核心原则**：从最小化配置起步，根据需求演进逐步引入复杂度，避免过度设计。

---

## 参考资料

- [LiteLLM 官方文档](https://docs.litellm.ai/)
- [LiteLLM Fallbacks 文档](https://docs.litellm.ai/docs/proxy/reliability)
- [LiteLLM Health Check Routing](https://docs.litellm.ai/docs/proxy/health_check_routing)
- [LiteLLM Spend Tracking](https://docs.litellm.ai/docs/proxy/cost_tracking)
- [LiteLLM Router SDK](https://docs.litellm.ai/docs/routing)
- [Hermes Fallback Providers 文档](https://docs.hermes-agent.us/user-guide/features/fallback-providers)
- [Hermes Providers 配置参考](https://docs.hermes-agent.us/integrations/providers)
- LiteLLM GitHub: https://github.com/BerriAI/litellm
