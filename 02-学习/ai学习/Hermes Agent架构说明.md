

《万字：OpenClaw vs Hermes》
## 五层架构

从你在终端敲下一句话，到最后一个字回到屏幕上，中间发生的所有事，就是这个Agent的全部骨架：一条消息从头跟到尾，就能顺出它背后的完整链路。

> 消息接收、平台适配、会话管理、上下文组装、记忆注入、技能发现、流式执行、工具调用、上下文压缩、子Agent分发、错误恢复与凭证轮换、状态持久化

所以，我们在终端敲hermes新起会话，输入：

> 帮我搜集今天的热点新闻
> 每条新闻要分类(科技、财经、社会、国际等)
> 并附上简要分析和总结

看起来一句话，但拆开来看，至少要做这些事：

1. 搜索当天的热点新闻
2. 对每条新闻做分类判断
3. 对每条新闻写简要分析
4. 整理成结构化的格式输出

这个过程涉及多轮工具调用（web_search搜新闻、web_extract提取详情）、信息整合、分类归纳。如果新闻来源多、数据量大，可能还需要拆分子任务并行搜集。

那Hermes Agent是怎么把这些事串起来的？先从整体架构说起。

- 入口层：CLI+二十多个消息平台适配器(飞书、钉钉、Telegram、Discord、Slack、WhatsApp、iMessage、Email、SMS……)
- 网关层：GatewayRunner常驻进程,管连接、会话生命周期、斜杠命令
- 执行层：AIAgent(run_agent.py),组装上下文、调模型、跑工具、处理错误,整个项目的心脏
- 扩展层：工具注册中心、技能系统、子Agent委托、MCP客户端、8个外部记忆Provider
- 存储层：SQLite+FTS5、MEMORY.md/USER.md、Skills目录、config.yaml、.env

一条消息的完整路径:

> 终端输入→CLI解析→会话加载→上下文组装→模型推理→工具执行→流式输出→状态落盘

下面我们一步步来看。

## 一、适配器模式的内外统一

终端是最直接的入口,但Hermes支持20+平台。每个平台消息格式都不一样:Telegram长轮询、Slack WebSocket、Email IMAP、SMS HTTP Webhook。

Hermes Agent给每个平台写了一个适配器，全部继承自BasePlatformAdapter。

> classBasePlatformAdapter(ABC):
> @abstractmethod
> async def connect(self) -> bool: ...
> @abstractmethod
> async def disconnect(self) -> None: ...
> @abstractmethod
> async def send(self, chat_id, content, reply_to=None, metadata=None) -> SendResult: ...

但这个基类里只定义了connect/disconnect/send,我们没有看到消息转换的接口定义，仔细看了下各个平台代码的实现，转换逻辑藏在每个适配器的connect()里,监听回调拿到平台原始消息后,自己构造MessageEvent,再交给基类统一处理。SMS适配器收到Twilio webhook时长这样:

> event = MessageEvent(
>     text=text,
>     message_type=MessageType.TEXT,
>     source=source,
>     raw_message=form,
>     message_id=message_sid,
> )

各平台的消息获取方式差异比较大,平台并没有抽象一个统一接口来处理消息转换。

所以它是约定而不是约束:各自监听、各自构造MessageEvent,后续所有代码对着同一个内部对象干活。

这是标准的适配器模式:进来时把外部差异统一成内部对象,出去时反向拆回各平台格式。不只是Agent开发,几乎所有要支持多平台的系统都会这么干。

## 二、Gateway的Profile隔离

Gateway启动按顺序做四件事:

- SSL证书自动探测(/etc/ssl/certs/ca-certificates.crt等路径逐个试,必须在任何HTTP库导入之前完成)、
- 加载~/.hermes/.env、
- 桥接config.yaml到环境变量(YAML支持${ENV_VAR}引用)、
- 启动启用的平台适配器。

这些都是工程标配，没有什么好说的。

值得一提的是Profile隔离:

> hermes profile create coder --clone #复制当前profile的配置、密钥、记忆
> hermes-p coder chat #一次性切换
> hermes profile use coder #设为默认
> coder chat #别名脚本,等同上面

每个Profile有独立配置、密钥、记忆、会话历史。实现靠一个HERMES_HOME环境变量,在CLI入口处、任何模块导入之前就设置好,所有后续代码通过get_hermes_home()拿主目录,切换时全自动生效。

删除profile：

> hermes profile delete coder #需输入名称确认
> hermes profile delete coder --yes #跳过确认直接删除

删除时会彻底清理:停Gateway进程→清理systemd/launchd服务→移除别名→删目录→如果是当前活跃profile就重置为default。

一个环境变量控制整棵目录树，切换不同的工作环境。于是你可以在一台机器上同时跑"工作Agent"和"个人Agent",互不打扰。

## 三、Agent主循环

消息到AIAgent，进入整个项目最核心的地方，这个地方一定要详细读、重复读：

主循环骨架

> while iteration_budget.remaining > 0:
>     response = client.chat.completions.create(
>         model=model, messages=messages, tools=tool_schemas, stream=True
>     )
>     if response 有 tool_calls:
>         执行工具(可能并行)
>         iteration_budget.consume()
>     else:
>         return response.content #没有工具调用,返回最终结果

主循环有三种退出路径：

- 模型给最终文本:本轮没有tool_calls,走else分支把response.content返回给用户,正常完结。
- 预算耗尽:while条件不再成立,iteration_budget.remaining归零。这是硬上限,防止模型在错误循环或幻觉里把token烧光。
- 用户中断:_interrupt_requested被外部置位。用户Ctrl+C或者直接发新消息都会触发,Agent在每轮开头检查这个标志。收到中断后不是raise抛异常,而是break出循环,持久化已有结果并补齐消息结构。

迭代预算

系统设计有循环迭代预算限制:父Agent上限90轮,子Agent 50轮。

模型每推理一轮消耗1次迭代预算,不管这一轮并行调了几个工具。

有意思的是refund()的触发条件:

> _tc_names = {tc.function.name for tcin assistant_message.tool_calls}
> if _tc_names == {"execute_code"}:
>     self.iteration_budget.refund()

当本轮工具调用里只有execute_code一种,刚扣掉的那1次迭代会被退还,这轮等于白送。

execute_code是PTC(Programmatic Tool Calling):模型不是直接挨个调工具,而是写一段Python脚本,脚本内部通过RPC把web_search、read_file、write_file这些工具串起来跑。

换个角度对比一下:同样要做8次信息获取,

- 走普通工具调用:模型调web_search→拿结果→再推理下一步调什么→调read_file→拿结果→再推理……8次工具执行要8轮模型推理,吃掉8次迭代预算。
- 走PTC:模型一轮里写出一整段脚本,脚本自己连调8次工具。1轮模型推理就打包干完。

PTC已经把8次工具调用折成1轮推理,系统再把这1轮也免掉,执行脚本在预算里等于零成本。

退还的真正作用是预算管理:脚本密集型任务可能要连写十几个脚本才做完,一次扣1轮的话,90轮预算很快被脚本执行吃掉,留给真正推理轮次的就不够了。索性让脚本执行零成本,预算就能全留给需要推理的轮次。

工具并行执行

系统维护三个集合决定一批工具能不能并行:

> _NEVER_PARALLEL_TOOLS = frozenset({"clarify"}) #会跟用户交互
> _PARALLEL_SAFE_TOOLS = frozenset({ #只读,无共享状态
>     "read_file","search_files","session_search",
>     "skill_view","skills_list",
>     "vision_analyze","web_extract","web_search",
>     "ha_get_state","ha_list_entities","ha_list_services",
> })
> _PATH_SCOPED_TOOLS = frozenset({"read_file","write_file","patch"}) #路径不重叠才能并行

路径工具的冲突检查原理:提取每次调用的目标路径,两两比对看有没有重叠。

重叠的判定包括两种情况:同一个路径,或者一个路径是另一个的祖先(比如/a和/a/b.txt)。

只要重叠,就可能撞上读写竞态(一个线程正在写,另一个读到半拉状态),必须排队串行;路径完全独立则放并行。

举两个例子:

- read_file("/a/b.txt")+write_file("/a/b.txt"):同一个文件,一个读一个写,并行会出乱子,必须串行
- read_file("/a/x.txt")+read_file("/b/y.txt"):两条路径完全独立,可以并行

并行池最多8个工作线程同时跑。

如果模型判断要同时读5个文件、搜2个关键词、查3个网页时,串行要10次API往返,并行可能2-3次搞定。每次API调用都是时间+金钱。

delegate_task

delegate_task是个特殊工具:模型选它的时候,会fork一个新的AIAgent。

子Agent有自己独立的上下文,也有自己独立的50轮迭代预算,父子之间只通过任务描述(传入)和最终摘要(传出)通信,除此之外彼此看不见。子Agent被禁用5个工具:

- delegate_task:防套娃。Agent嵌套本身就有开销,再允许无限递归成本会爆
- clarify:子Agent不能反问人,因为用户不在场,只有父Agent是跟人对话的那一层
- memory:子Agent不能写共享记忆,避免一次临时委托里抓到的噪声,污染所有未来会话
- send_message:子Agent不能直接往平台发消息,对外沟通只能经由父Agent
- execute_code:子Agent定位就是一步步推理把事做完,不该再用PTC折叠(PTC是主Agent用来节省轮次的,子Agent本来就分到了独立预算,用不着)

结构上还有两条硬约束:委托深度只有1层(父→子,子Agent禁用了delegate_task无法再委托)、并发上限3个。

父Agent每30秒给子发一次心跳,一旦父被用户中断或者自己挂了,心跳断开,子Agent就会连锁停下,这就是"级联中断"。没有这个机制,用户按了Ctrl+C之后,后台还会有一堆子Agent继续烧token。

子Agent的系统提示词强调的是边界而不是人格:做这一件事、给摘要、不用关心父Agent在干什么。

主Agent的上下文只会看到委托调用本身和最终摘要,看不到子Agent那可能20次工具调用的中间过程。

主Agent能处理多少轮用户消息才触顶上下文压缩,取决于它的上下文保持得多干净,一次把重活甩给子Agent、只把摘要收回来,等于用一点并行开销换主Agent的长寿。

回到开头那个新闻例子:主Agent给科技/财经/国际各委托一个子Agent并行跑,拿摘要自己汇总分类。主Agent只花1次迭代预算,子Agent的50次预算各自独立。

## 四、系统提示词

模型推理之前,系统提示词要拼好。实际顺序:

> 身份→工具行为引导→外部系统提示→记忆→技能索引→项目上下文→运行时元数据(时间/环境/平台)

每一层都有什么，我们简单看下:

- 身份:默认是一段"You are Hermes Agent..."的声明。用户在~/.hermes/SOUL.md里写了自定义人格就会替换掉默认那段。
- 工具行为引导:下面单独讲,这一层信息密度最高,还会根据模型家族(GPT/Gemini/Grok/Claude)注入不同内容。
- 外部系统提示:网关层、API或用户配置注入的补充指令,可选。
- 记忆:MEMORY.md(Agent笔记)、USER.md(用户画像),加上可选的外部记忆Provider回忆到的内容,Step 5细讲。
- 技能索引:只放一个紧凑目录(标签包起来),模型看到目录后通过skill_view工具按需加载完整技能内容,不是启动时就全塞进来。
- 项目上下文:从工作区扫到的.hermes.md/AGENTS.md/CLAUDE.md等指令文件,注入前要过安全扫描,下面讲。
- 运行时元数据:当前时间、WSL/Termux等特殊环境提示、以及飞书/Discord/Telegram这些消息平台的格式约定(比如WhatsApp不渲染Markdown)。

这个顺序的门道:越稳定的内容越靠前,动态内容靠后。配合前缀缓存,前缀不变就能命中,只有尾巴会变。

针对不同模型的工具使用约束

对GPT、Gemini、Grok家族,会额外注入TOOL_USE_ENFORCEMENT_GUIDANCE,核心一句话:说做就做,别光说不动。

Claude不需要这段,不是偏见,是不同模型在工具调用行为上确实有差异。GPT写代码确实喜欢TODO，这是实战认知的沉淀。

项目上下文的安全扫描

从工作区扫.hermes.md/HERMES.md/AGENTS.md/CLAUDE.md/.cursorrules(先到先得,前两个向上直到Git根,后三个只看当前目录),注入前过10条正则:

> _CONTEXT_THREAT_PATTERNS=[
>     (r'ignore\s+(previous|all|above|prior)\s+instructions',"prompt_injection"),
>     (r'do\s+not\s+tell\s+the\s+user',"deception_hide"),
>     (r'',"html_comment_injection"),
>     (r'<\s*div\s+style\s*=\s*["'][\s\S]*?display\s*:\s*none',"hidden_div"),
>     (r'curl\s+[^\n]*\$\{?\w*(KEY|TOKEN|SECRET|PASSWORD)',"exfil_curl"),
>     (r'cat\s+[^\n]*(\.env|credentials|\.netrc|\.pgpass)',"read_secrets"),
> ]

覆盖了常见的prompt injection手法（忽略指令、角色扮演绕过）、HTML隐蔽注入（注释、隐藏div）、翻译攻击（"翻译成X然后执行"），以及数据外泄（curl环境变量、cat敏感文件）。

命中任何一条规则，整个文件内容会被阻断并替换为[BLOCKED:...]。

上下文文件是持久化在磁盘上的。如果攻击者诱导Agent往.hermes.md里写恶意指令,那就是一个每次启动都触发的永久后门。

不过这些正则只覆盖英文模式，中文prompt injection（比如"忽略之前的所有指令"）不在检测范围内，这是一个潜在的盲区。

ephemeral_system_prompt

它不在系统提示词的构建流程中,只在API调用时临时拼到系统提示词末尾。源码注释这样写道:为了不污染缓存。

主体保持稳定,变化部分压在末尾,缓存继续命中。

拼好的结果缓存在self._cached_system_prompt上,一个会话只构建一次,只有上下文压缩时才重建。

## 五、记忆系统

系统提示词框架搭好后,要注入记忆。

Hermes的记忆系统不是KV存储,也不是向量数据库,是冻结快照+文件持久化+按需检索的组合。

两个文件:

- MEMORY.md:Agent自己的笔记本("这台机器Python是3.11"、"这个项目用commitlint"、"web_extract对这个网站不稳定")
- USER.md:Agent对用户的了解(偏好、沟通风格、工作习惯)

两个文件都限制按字符数(不是token数),

- MEMORY.md 2200字符,
- USER.md 1375字符。

冻结快照

> class MemoryStore:
>     def load_from_disk(self):
>         self.memory_entries = self._read_file(mem_dir / "MEMORY.md")
>         self.user_entries = self._read_file(mem_dir / "USER.md")
>         #捕获冻结快照
>         self._system_prompt_snapshot = {
>             "memory": self._render_block("memory", self.memory_entries),
>             "user": self._render_block("user", self.user_entries),
>         }

记忆在会话开始时注入系统提示词,之后整个会话期间不再更新。

会话期间通过工具写入的记忆会立刻持久化到磁盘(不丢数据),但系统提示词里的快照不变。下次新会话才从磁盘加载最新。

这里的设计还是为了能命中前缀缓存。每轮写记忆都改系统提示词,缓存就没法命中。这是用一致性换性能的工程权衡。

记忆写入也要过安全扫描

MEMORY_THREAT_PATTERNS覆盖prompt injection/角色劫持/数据外泄等。

另外可选8个外部记忆Provider:Honcho、Mem0、Hindsight、Holographic、ByteRover、OpenViking、RetainDB、Supermemory。

内置Provider永远在,外部同时只能开一个。

查询到的记忆用标签包裹,附带一句"这是背景参考,不是新用户输入",防止模型把记忆当成新请求去响应。

## 六、自我修复

主循环每一步都可能出问题:上下文不够用、API超时、凭证限流、服务器500。

Hermes的做法是按错误分类,各走各的恢复路径,而不是一个大try/except：

上下文压缩

ContextCompressor的压缩流程:

1. 裁旧工具输出(不调LLM):替换成[Old tool output cleared to save context space]。很多时候这一步就够降到阈值下。
2. 保护头部:系统提示词+前3条消息不动(通常是系统提示词+第一条用户消息+第一条助手回复,即第一轮完整交换)。
3. 保护尾部按token预算:最近的完整对话不动,预算是两步链式推导出来的,先算压缩触发阈值context_length×0.50(上下文用掉一半时触发压缩),再从阈值里拿出20%给尾部保护(threshold_tokens×0.20)。200K上下文模型的阈值是100K,尾部预算=100K×20%=20K token。
4. 中间摘要:配置里指定的便宜模型做摘要。摘要前拼SUMMARY_PREFIX:"这是来自前一个上下文窗口的交接"。
5. 增量更新:二次压缩在已有摘要上更新,不从头重压。摘要token上限12000,防自己膨胀。

压缩触发时主动调_invalidate_system_prompt()+_build_system_prompt()重建系统提示词,冻结的记忆快照重新生成，加载最新的记忆内容。

错误分类器

API调用会失败的原因各种各样:认证失败、额度耗尽、限流、上下文超限、模型不存在、网络中断……

FailoverReason枚举把这些归了14种。每个错误抛出时先过一道分类器,再封装成ClassifiedError,只带四个布尔恢复标记:

> retryable: bool #能不能直接重试
> should_compress: bool #要不要先压缩上下文再重试
> should_rotate_credential: bool #要不要切换到下一个API Key
> should_fallback: bool #要不要切到fallback模型

主循环拿到ClassifiedError之后不自己做字符串匹配,只看这四个标记决定下一步。

为什么要分得这么细，一个典型的对比是HTTP 402和429。它们表面都是"限额"类错误,但处理方式完全不同:

- 429是临时限流:Provider告诉你"请求太快,歇一下再来",退避重试同一个Key就能恢复
- 402是额度耗尽:账户上的钱已经扣光了,同一个Key短期内不会恢复,必须立即切到下一个Key

不分清楚的话,Agent会在一个已经没钱的Key上反复退避到天荒地老。

分类器把这两种错误映射到不同的恢复标记组合(429置retryable=True,402置should_rotate_credential=True),主循环看标记就知道该退避还是该换钥匙。

用户中断

每轮开头检查_interrupt_requested。用户Ctrl+C或发新消息触发时不raise而是break:持久化已有结果,返回interrupted=True。

如果前面tool_calls已追加但没执行,会补一个伪造的错误tool result,保证消息结构对API合法,下次恢复对话不会被Provider拒。

## 七、消息返回

模型给了最终回答,文本沿着和进来相反的方向走回去。

流式token通过_fire_stream_delta()边生成边推。CLI下直接写进prompt_toolkit的patch_stdout,Gateway下由stream_consumer.py按1秒节流编辑同一条消息。

附件的处理方式。

> 在文本里加MEDIA:/absolute/path/to/file前缀就能发附件

Gateway侧在文本展示前把MEDIA:指令剥掉,交给对应平台适配器转成各自的附件API:飞书走上传素材接口,Discord拼file attachment,iMessage走BlueBubbles的attachment字段。

一进一出,两层适配把平台差异挡在核心之外:

> 进来把各平台消息统一成MessageEvent,出去把统一格式的MEDIA:再拆回各平台附件机制。

核心代码(主循环、工具、记忆、技能)从头到尾只跟统一协议打交道,不用知道消息从哪来、要到哪去。想接新平台,写一个适配器就够。

## 八、自进化

这里又是核心了，也是Hermes区别于OpenClaw的所在：

模型给了最终回答,终端/平台也推送完了。这时候如果什么都不做,这一轮产生的经验都会随进程退出蒸发。

run_conversation()返回前还有三件事:落盘、记忆同步、后台复盘。都在用户看完回复、Agent表面"闲下来"之后发生,对用户零感知。

记忆同步

- 内置MEMORY.md/USER.md:每次memory工具调用立刻atomic rename写磁盘;下次新会话load_from_disk()时快照才刷新。既保前缀缓存命中,又不丢数据。
- 外部Provider:每轮结束调sync_all(用户原话,最终回复),推整轮交换给Provider,让它自己抽事实;on_session_end不是每轮调,只在CLI退出、/reset或Gateway判定会话过期时调一次。

后台复盘

这里是真正让它"自进化"的地方,先把这个"技能"概念铺一下,否则这一节不好读。

Hermes的技能(Skills)是存在Skills目录里的一堆Markdown文档,每一篇是一段"做过之后沉淀下来的操作笔记"。

会话启动时,这些文档的标题和简介会被拼成一个紧凑目录塞进系统提示词。模型在对话里遇到相关任务,看到目录条目,再用skill_view按需加载完整内容。

技能越攒越多,Agent下次做类似任务就越不用从头摸索,这是"自进化"的物质基础。

但技能不会自己长出来,得有人(或Agent自己)往目录里写。Hermes的做法是两条信号并行:

信号一:系统提示词里的主动引导。SKILLS_GUIDANCE告诉模型"复杂任务完成后主动存、用到过时的技能立即patch",让模型在合适的时刻自己调skill_manage写文件。

信号二:后台强制复盘。默认_skill_nudge_interval=10,每消耗10次模型推理轮次触发一次"技能复盘",和Step 3的迭代预算是同一个计数口径。

如果这10轮里Agent自己已经调过skill_manage(说明信号一生效了),计数器会被重置,再过10轮才会再触发,避免刚存完又逼着复盘一次。

复盘触发后,_spawn_background_review()在一个独立的后台线程里再fork一个mini Agent出来:max_iterations=8,quiet_mode=True,任务是判断这段对话有没有非平凡的方法,有就存成新技能或更新现有技能,没有就退出。

> Background memory/skill review—runs AFTER the response is delivered so it never competes with the user's task for model attention.

背景线程必须在回复已经发给用户之后才启动,绝对不和用户正在等的响应抢模型资源。

这就是所谓"自进化"真正发生的地方:用户看不到它学,但每过10轮模型推理,就可能有一段新的经验被沉淀进技能库。下一次遇到类似任务,它就不用从头摸索了。

上下文压缩

上下文压缩有一个很容易被忽略的副作用:摘要是有损的。

Hermes的做法是，每次上下文压缩时,SessionDB里做三件事:

1. 结束当前session,原始对话完整保留在数据库里,不删
2. 开一个新session,把压缩后的摘要作为新session的起点
3. 新session的parent_session_id指回旧session的ID

这样设计之后,"省成本"和"不丢历史"两个看起来矛盾的目标,用分层各自满足:

- 模型层(当前session):只装系统提示词+摘要+近期对话,token成本不会随对话无限膨胀
- 数据层(SQLite):所有session的原始消息全部留着,FTS5索引全文可搜

模型看到的是压缩版,数据库存的是完整版。两个目标不是真的矛盾,只是不该用同一份数据同时扛。

但要注意,"能搜到历史"和"Agent记住了"是两回事。

session_search是按需检索:模型得主动调用这个工具才能拿到旧对话的片段,搜索结果只是当次推理的临时上下文,不会自动写入MEMORY.md。

真正持久的"记忆"只有一条路:模型主动调memory工具写入,下次新会话启动时才从磁盘加载进快照。

换句话说,session链保的是原始数据不丢,记忆系统保的是经验沉淀不丢,两条通道各管各的。
