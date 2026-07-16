# theNanGuos（南郭先生们）产品需求文档

## 1. 文档职责

本文定义产品为什么存在、服务谁、提供什么能力以及哪些业务规则不可破坏。字段级合同见 [数据模型](../architecture/DATA_MODEL.md)，接口见 [API 合同](../architecture/API_SPEC.md)，Agent 和记忆机制见 [Agent 系统](../architecture/AGENT_SYSTEM.md)，当前完成度只见 [开发状态](../planning/STATUS.md)。

## 2. 产品定位

theNanGuos 是本地单用户音乐生成 Web 应用，同时保留可测试的 CLI。用户用自然语言描述歌曲，四个固定职责 Agent 将模糊要求转换成可校验的创作计划和 Suno 请求；后端轮询生成状态，按用户本次选择保留 1、2 或全部候选 MP3 和 Suno 封面，供用户播放、下载和管理。

产品重点不是自研音频渲染或 DAW，而是形成以下闭环：

1. 自然语言需求；
2. 可解释的创作计划；
3. 可校验的结构化音乐信息；
4. 可追踪的 Agent 协作与外部请求；
5. 可长期保留的本地作品。

## 3. 产品目标

- 以自然语言为主入口，降低音乐参数填写门槛。
- 使用 Conductor、Lyrics、MusicPlanner、Arrangement 四个 Agent 分工创作。
- 使用确定性 Tool 完成校验、Suno 请求构造、轮询和文件保存。
- 提供创作、等待、结果、作品、偏好五页 Web 体验。
- 完整校验供应商候选后，按响应顺序将本次选择的候选 MP3 和 Suno `imageUrl` 封面保存到本地；默认保留 1 首。
- 区分单次运行状态、用户确认型偏好和人工创作知识。
- 不向前端和产物暴露密钥、Authorization、隐藏推理或完整供应商原始响应。
- 保留 CLI `--no-submit`，支持不访问 Suno 的结构化产物检查。

## 4. 非目标

- 不实现登录、多用户、权限、云端账号和公网部署。
- 不实现分布式队列、多 FastAPI 进程协调或 LangGraph 跨进程恢复。
- 不撤销 Suno 远程任务；“停止等待”只停止本地轮询。
- 不生成 MIDI、MusicXML、ABC notation、逐音符乐谱或自研 demo 音频。
- 不使用参考音频上传、翻唱、音频延长或 upload-cover 流程。
- 不调用 DeepSeek 或其他模型生成封面；封面只来自 Suno 音乐结果。
- 不实现 DAW、分轨、混音、母带或音频区域编辑。
- 不从一次生成自动学习用户习惯，也不维护 `run_lessons`。
- 第一版不提供知识库管理页面、向量数据库或 Agent 自动写回知识。

## 5. 用户与场景

MVP 只有一个本地用户。用户希望：

- 用一句话快速生成完整歌曲；
- 在提交前看懂并调整系统形成的创作方案；
- 调整语言、纯音乐、人声、模型、本地保留数量和高级 Suno 权重；本地保留数量不改变供应商生成数量或费用。
- 查看 Agent 阶段与 Suno 真实离散状态；
- 离开等待页后继续从作品页查看任务；
- 停止本地轮询，并稍后按 `taskId` 继续查询；
- 试听和下载多个候选版本；
- 保存主动确认的默认参数和手工风格说明；
- 使用维护者整理的风格、乐器和经典曲目抽象知识辅助创作。

## 6. 核心用户流程

### 6.1 Web 主流程

1. 用户输入自然语言创作描述和本次覆盖参数。
2. 系统运行 Conductor，返回进程内创作预览、`SongSpec` 和解释性 `TaskPlan`。
3. 用户检查系统复述并编辑标题、风格、情绪、语言、人声、时长、结构和避免项。
4. 用户确认后提交；预览被一次性消费，后端复用已确认结果并立即返回 `request_id`。
5. Lyrics 生成分段歌词；MusicPlanner 规划曲式、BPM、Key、和弦和旋律意图；Arrangement 规划乐器、制作和 Suno style。
6. 系统形成 `ScorePlan` 和经校验的 Suno 请求。
7. 后端提交 Suno，立即首次查询，随后默认每 30 秒轮询。
8. 成功后先校验全部供应商候选，再按本次 `retention_limit` 下载前 1、前 2 或全部候选及存在的封面，跳转结果页。
9. 用户在线播放、拖动进度、调节音量、逐首下载，或回作品页管理历史任务。

预览默认 30 分钟过期、只能消费一次且不跨服务重启。预览失效时保留用户输入，允许重新生成方案。正式生成不能再次调用 Conductor。

### 6.2 等待与恢复

- 等待页展示 Agent 业务阶段和 Suno 状态文字。
- 百分比只表示离散状态区间内的预计进度，不能冒充供应商真实连续进度。
- `FIRST_SUCCESS` 表示第一首已完成但仍等待全部结果。
- “停止等待”不声称撤销远程任务。
- 已停止或服务中断的任务保留 `taskId`，可从作品页继续查询。
- 服务重启不恢复原 LangGraph；启动索引将未完成远程任务标为“服务中断”。

### 6.3 CLI 流程

CLI 复用同一服务层和 LangGraph。`--no-submit` 生成并校验本地产物，不访问 Suno；CLI 不经过 Web 预览 API，但不能绕过 Schema、Agent、Tool 或日志边界。

## 7. 产品能力

### 7.1 创作与确认

自然语言是第一层输入。用户可以调整产品级创作方案，但不能直接编辑 GraphState、prompt 或供应商 JSON。显式标题覆盖模型推断标题；空标题不作为覆盖值。

### 7.2 Agent 创作

四个 Agent 依次完成需求标准化、歌词、音乐规划和编曲。固定 LangGraph 决定执行拓扑，`TaskPlan` 只用于解释目标、节点指令和依赖，不动态改变图。

### 7.3 Suno 生成

系统通过 Kie.ai 向 Suno 提交通过合同校验的请求。结果固定使用轮询获取；`callBackUrl` 只满足供应商必填合同，不作为本地结果来源。`retention_limit` 是本地字段，不进入供应商 payload；成功后只保存所选候选的音频和封面，本地媒体优先于可能过期的供应商 URL。

### 7.4 作品管理

作品页从本地协作日志重建索引，支持搜索、状态筛选、时间排序、首候选快捷播放、进入结果页选择具体版本、继续查询和不可恢复地删除整次生成任务。删除运行中任务必须拒绝；删除 stopped/interrupted 任务前必须提示将失去继续查询所需的本地 taskId。空列表必须显示真实空态，不能用 demo 数据冒充作品。

### 7.5 用户偏好

确认型 JSON 只保存语言、纯音乐、人声和 Suno 模型；风格 Markdown 只由用户编辑。清除偏好需要二次确认，且不能删除作品。标题、歌词和单次创意不得进入默认偏好。

### 7.6 创作知识

人工知识库保存风格、乐器和经典曲目抽象分析。用户偏好回答“用户喜欢什么”；知识库回答“音乐概念有什么可参考特征”。两者可以进入 Agent 上下文，但不得互相写入或自动转化。

经典曲目不得保存歌词、音频、逐音符旋律或大段受版权保护内容，Agent 不能被要求复刻具体作品。知识故障不得阻断基础生成。

## 8. 核心对象词汇表

| 对象 | 产品含义 | 主要生产者 | 主要消费者 | 字段权威 |
|---|---|---|---|---|
| GenerationPreview | 用户提交前可检查和修改的临时创作方案 | Conductor | 创作页、创建接口 | [DM-GenerationPreview](../architecture/DATA_MODEL.md#dm-generationpreview) |
| SongSpec | 一首歌的标准化创作意图 | Conductor、用户确认 | 三个专业 Agent、Suno builder | [DM-SongSpec](../architecture/DATA_MODEL.md#dm-songspec) |
| TaskPlan | 对固定图执行目标和依赖的解释 | Conductor | LangGraph 日志和开发者 | [DM-TaskPlan](../architecture/DATA_MODEL.md#dm-taskplan) |
| ScorePlan | 歌词、音乐和编曲结果的统一计划 | 生成服务 | Suno builder、产物 | [DM-ScorePlan](../architecture/DATA_MODEL.md#dm-scoreplan) |
| Generation | 一次生成任务及其生命周期 | FastAPI/TaskRegistry | 等待页、结果页、作品页 | [DM-GenerationRecord](../architecture/DATA_MODEL.md#dm-generationrecord) |
| SunoTask | 远程生成任务和候选歌曲 | Suno | 轮询器、媒体保存 | [DM-SunoTaskDetails](../architecture/DATA_MODEL.md#dm-sunotaskdetails) |
| Work | 本地可播放和下载的最终候选作品 | ArtifactStore | 结果页、作品页 | [本地作品视图](../architecture/DATA_MODEL.md#本地作品视图) |
| UserPreference | 用户主动确认的默认值和风格说明 | 用户 | Conductor、创建页 | [偏好模型](../architecture/DATA_MODEL.md#用户偏好模型) |
| KnowledgeContext | 单次生成检索到的只读参考 | Retriever | 各 Agent 职责视图 | [DM-KnowledgeContext](../architecture/DATA_MODEL.md#dm-knowledgecontext) |

## 9. 核心业务规则

1. 正式生成产出 `song_spec.json`、`score_plan.json`、`suno_request.json`、`collaboration_log.json`。
2. Agent 不直接写文件或调用 Suno；确定性 Tool 不重新创作。
3. LLM 最终内容必须通过 Pydantic 校验，空内容、截断、非法 JSON 或结构失败最多重试两次。
4. 当前自然语言明确要求优先于 Web/CLI 显式字段，显式字段优先于长期偏好，长期偏好优先于系统默认。
5. Suno 请求不得静默截断超限文本。
6. `PENDING`、`TEXT_SUCCESS`、`FIRST_SUCCESS` 继续；`SUCCESS` 完成；已知失败、未知状态和空结果终止。
7. 媒体只接受任务元数据记录的 HTTPS URL，拒绝私网、localhost 和重定向，使用流式下载和原子替换。
8. API 和日志不得包含密钥、Authorization、隐藏推理、完整 prompt 摘录或完整供应商原始 JSON。
9. 知识库只读；Lyrics 不取得经典曲目分析；Suno builder 不直接访问知识库。
10. 正常产品路径不得隐式注入 demo 数据；视觉样例只能由显式开关启用。

## 10. 产品级异常与边界

- 预览不存在、过期或已消费：提示重新生成方案，保留用户输入。
- LLM 结构化输出持续失败：终止任务并显示可操作错误，不显示隐藏推理。
- Suno 认证、参数或业务失败：终止，不把失败描述成超时。
- 连接错误、429、5xx：只在总截止时间内有限重试。
- 用户停止等待：状态变为已停止等待，远程任务可能继续。
- 服务重启：未完成任务标记服务中断，用户可继续查询；不声称恢复原图。
- 单个媒体下载失败：保存结构化错误，不提供不存在的本地播放地址。
- 知识文件非法或知识库不可用：隔离坏条目或整体降级，基础生成继续。

## 11. 产品验收标准

- 用户可以完成“描述 → 预览 → 确认 → 等待 → 结果 → 播放/下载”闭环。
- 停止等待后可以从作品页继续查询。
- 作品页可进入既有结果页选择每个已保留版本；播放进度来自真实音频时间，每个候选音量互不联动。
- completed、failed、stopped、interrupted 任务可经二次确认整次删除；queued/running 任务不可删除。
- 保存和清除偏好不会删除作品，也不会保存标题和歌词。
- 五页正常路径使用真实 API 数据；演示数据必须显式启用。
- 本地作品优先使用已保存的 MP3 和封面。
- 后端 Schema、DeepSeek、Suno、文件安全、API、知识库均有确定性测试。
- 前端具备单元、类型、构建和真实浏览器 Mock 全栈验证。
- 五页在 1440×1024 与已确认原型复核。
- 真实 DeepSeek 和 Suno 最小联调分别完成后，才能将对应 Milestone 标为完成。

## 12. 相关文档

- [功能行为规格](SPEC.md)
- [Web UI 设计](WEB_UI_DESIGN.md)
- [系统架构](../architecture/ARCHITECTURE.md)
- [信息架构](../architecture/INFORMATION_ARCHITECTURE.md)
- [Agent 系统](../architecture/AGENT_SYSTEM.md)
- [数据模型](../architecture/DATA_MODEL.md)
- [API 合同](../architecture/API_SPEC.md)
