# theNanGuos API 与供应商协议合同

## 1. 文档职责

本文定义本地 FastAPI、DeepSeek 和 Suno 的请求、响应、状态、错误、超时与安全边界。对象字段见 [数据模型](DATA_MODEL.md)，用户可见行为见 [功能规格](../product/SPEC.md)。

## 2. 通用约定

- 后端默认 `http://127.0.0.1:8000`，开发 CORS 只允许 localhost/127.0.0.1:5173。
- JSON 请求使用严格模型，未知字段返回 422。
- 不实现认证；只适用于本地单用户、非公网环境。
- 错误 detail 对用户可操作，不包含堆栈、密钥、Authorization、隐藏推理和完整供应商响应。
- `/api/generations` 创建返回 202；预览创建当前返回 200。

## 3. 本地 FastAPI

### API-PREVIEW-001 创建创作预览

`POST /api/generation-previews`

请求使用 CreateGeneration；正常 Web 请求提供 prompt/overrides，不提供 preview_id/approved_song_spec。响应：preview_id、song_spec、task_plan。

| 状态 | 条件 |
|---|---|
| 200 | 预览成功 |
| 422 | 请求字段非法 |
| 503 | 未配置 previewer |

预览存于进程内字典，TTL 1800 秒；消费时原子 pop。当前实现没有独立预览查询/删除接口。

### API-GEN-001 创建生成任务

`POST /api/generations`，成功 202。

Web 两阶段请求同时提供 preview_id 和 approved_song_spec；后端验证 preview 存在、prompt 一致、未过期且未消费，然后复用 preview TaskPlan。当前 CreateGeneration 也允许两者同时缺失，供测试/兼容的单阶段创建路径使用。

顶层 `retention_limit` 只允许严格整数 1、2 或 null，缺省为 1，null 表示本地保留全部供应商候选。该字段不进入 GenerationOverrides、用户偏好或 Kie/Suno payload。

| 状态 | 条件 |
|---|---|
| 202 | 记录登记并启动后台 runner |
| 409 | preview 不存在、过期、已使用或 prompt 不一致 |
| 422 | preview_id/approved_song_spec 只提供一个或字段非法 |

响应：`{"request_id": "<32 hex>", "status": "queued"}`。

### API-GEN-LIST-001 列表和详情

- `GET /api/generations?search=&status=&sort=newest|oldest`
- `GET /api/generations/{request_id}`

列表响应 `{"items": [...]}`；search 匹配用户请求或候选标题，status 精确匹配产品状态，默认按 created_at 降序。详情不存在返回 404。

公开记录字段见 [DM-GenerationRecord](DATA_MODEL.md#dm-generationrecord)。

### API-GEN-DELETE-001 删除整次生成任务

`DELETE /api/generations/{request_id}`，成功 204。completed、failed、stopped、interrupted 可删除；queued、running 或仍有未结束后台 task 时返回 409。不存在返回 404。

服务端只从已登记 request_id 构造 outputs 直属子目录，拒绝根目录、越界、非法 ID、符号链接和非目录目标。文件系统删除成功后才移除 TaskRegistry 记录；Windows 文件占用等删除失败返回 500 安全文案并保留记录。该接口删除整次任务的 JSON、已保留音频和封面，不删除 Suno 远程任务，也不提供回收站或撤销。

### API-WAIT-001 停止等待与继续查询

- `POST /api/generations/{request_id}/stop-waiting`：200。
- `POST /api/generations/{request_id}/resume-polling`：202。

停止设置 stop_event、产品状态 stopped/stopped_waiting，并尽力把日志 Suno 状态写为 STOPPED_WAITING。响应明确“远程生成可能继续”。

继续要求 record 和 task_id；无远程任务返回 409，runner 未配置返回 503。继续重置 asyncio.Event，设置 queued/resume_polling，并启动新 runner。

### API-MEDIA-001 音频、下载和封面

- `GET /api/generations/{request_id}/audio/{audio_id}`
- `GET /api/generations/{request_id}/audio/{audio_id}/download`
- `GET /api/generations/{request_id}/cover/{audio_id}`

request_id/audio_id 只允许字母、数字、下划线、连字符。音频必须同时存在 MP3 和协作日志 audio_results 元数据。

音频无 Range 返回 FileResponse 和 `Accept-Ranges: bytes`；单范围请求返回 206、Content-Range、Content-Length。不合法或不可满足范围返回 416。下载使用 Suno 标题的安全文件名和 `.mp3`。封面只在 covers 下恰好匹配一个 `audio_id.*` 时返回。

媒体不存在或元数据不一致返回 404。

### API-PREF-001 偏好

- `GET /api/preferences`：返回 defaults 和 style_markdown。
- `PUT /api/preferences/defaults`：请求 UserProfile，返回保存值。
- `PUT /api/preferences/style`：请求 `{"markdown": "..."}`，最长 100000。
- `DELETE /api/preferences`：204，无响应体。

偏好无作品删除副作用。

## 4. DeepSeek 协议

官方参考：[JSON Output](https://api-docs.deepseek.com/guides/json_mode)、[Thinking Mode](https://api-docs.deepseek.com/guides/thinking_mode)。本节记录项目在官方协议之上的固定适配约束。

### API-LLM-001 结构化生成

环境变量：

- `DEEPSEEK_API_KEY`；
- `DEEPSEEK_BASE_URL`，默认 `https://api.deepseek.com`；
- `DEEPSEEK_MODEL`，默认 `deepseek-v4-pro`。

CLI 与 FastAPI 模块启动时自动从当前目录向上查找最近的 `.env`；显式进程环境变量优先，不会被文件值覆盖。

客户端使用 OpenAI-compatible chat completions：

- `response_format={"type":"json_object"}`；
- `extra_body={"thinking":{"type":"enabled"}}`；
- 不为思考模式发送无效 temperature/top_p；
- system message 包含目标 JSON Schema；user message 是业务 payload JSON。

只解析最终 `content`。`reasoning_content` 不返回 Agent、不写日志、不进入作品或记忆。

空内容、截断、非法 JSON 或 Pydantic 失败最多重试两次；仍失败抛出结构化 LLM 错误。认证和网络错误不能在日志中包含 key/header。

## 5. Kie.ai Suno 生成协议

官方参考：[生成音乐](https://docs.kie.ai/cn/suno-api/generate-music)、[获取音乐生成详情](https://docs.kie.ai/cn/suno-api/get-music-details)、[音乐生成回调](https://docs.kie.ai/cn/suno-api/generate-music-callbacks)。依据当前集成合同：

- Base URL 环境变量 `KIE_BASE_URL`，运行时默认 `https://api.kie.ai`；
- API key 优先读取 `KIE_API_KEY`；
- callback URL 优先读取 `KIE_CALLBACK_URL`，未配置时使用 `https://callback.invalid/kie/suno` 占位；
- 旧 `SUNO_API_KEY`、`SUNO_BASE_URL`、`SUNO_CALLBACK_URL` 仅作为兼容回退；
- 结果来源固定为详情轮询，不依赖回调；占位回调不得使用无关的真实网站。

### API-SUNO-GEN-001 提交音乐生成

`POST /api/v1/generate`

成功从响应 data.taskId 取得任务标识。请求 JSON 使用 camelCase。

| 模式 | 必填创作字段 | 禁止 |
|---|---|---|
| customMode=true, instrumental=false | prompt、style、title | 无 |
| customMode=true, instrumental=true | style、title | prompt 可空 |
| customMode=false | prompt | style、title、negativeTags、vocalGender、三个权重必须空 |

所有模式均要求 customMode、instrumental、model、callBackUrl。

| 字段 | 约束 |
|---|---|
| model | V4、V4_5、V4_5PLUS、V4_5ALL、V5、V5_5 |
| vocalGender | m、f 或空 |
| 三个权重 | 0–1 |
| custom prompt | V4 最长 3000；其他模型 5000 |
| style | V4 最长 200；其他模型 1000 |
| title | 所有模型最长 80 |
| non-custom prompt | 最长 500 |

超限校验失败，不静默截断。

### API-SUNO-POLL-001 查询与轮询

`GET /api/v1/generate/record-info?taskId=<task_id>`

任务详情在响应 data，候选在 data.response.sunoData。模型把候选展平为 audio_results。真实 Kie 响应可能在进行中状态提前返回字段不完整的候选，因此只有 `SUCCESS` 或带完整结果的可恢复 `CALLBACK_EXCEPTION` 才解析最终媒体对象；进行中状态只消费任务状态。

| 分类 | 状态 | 行为 |
|---|---|---|
| 进行中 | PENDING、TEXT_SUCCESS、FIRST_SUCCESS | 记录并继续 |
| 成功 | SUCCESS | 要求非空候选，结束 |
| 失败 | CREATE_TASK_FAILED、GENERATE_AUDIO_FAILED、SENSITIVE_WORD_ERROR | 立即业务失败 |
| 回调失败 | CALLBACK_EXCEPTION | 有非空 sunoData 时按轮询结果继续保存；无结果时业务失败 |
| 未知 | 其他 | 协议错误，立即终止 |

轮询算法：

1. 单调时钟记录统一截止时间。
2. 提交后立即第一次详情查询。
3. 只有进行中状态才等待 interval；默认 30 秒。
4. 每次请求前计算剩余时间；默认总等待 1200 秒。
5. 连接错误、响应头前断连、429、5xx 可在总期限内有限重试。
6. 认证、参数、业务终态、未知状态不重试。
7. SUCCESS 但 sunoData 缺失或为空仍失败；CALLBACK_EXCEPTION 只有在携带非空 sunoData 时可恢复。
8. stop_event 被设置时抛出本地停止异常，不声称撤销远程任务。
9. 最终响应先完整解析所有候选，再按本地 retention_limit 和响应顺序保留前 N 个；只有保留项进入下载、公开 API 和日志。日志记录 provider_candidate_count、retention_limit、retained_candidate_count，未保留媒体 URL 不落盘。

## 6. 媒体下载协议

SunoAudio 的 audioUrl/streamAudioUrl/imageUrl 以及 Kie 返回的 sourceAudioUrl/sourceStreamAudioUrl/sourceImageUrl 必须是 HTTPS。下载优先使用常规媒体 URL，source URL 作为供应商原始地址保留在严格模型中。ArtifactStore 只接受当前响应中记录的 URL 集合，并在下载前验证：

- scheme 为 HTTPS；
- hostname 不是 localhost；
- DNS 解析结果都是公网地址；
- 客户端不跟随重定向；
- Content-Length 和流式累计大小不超过上限；
- 请求和读取分别受超时限制。

数据先写 `.tmp`，成功后 `os.replace`。响应头前断连等传输错误最多重试三次，每次重试前删除部分临时文件；HTTP 状态错误、大小越界和 URL 安全错误不按该规则重试。日志中的所有常规/source 媒体 URL 与 local_media.source_url 都去掉 query，本地只记录相对 outputs 路径。

## 7. 错误与重试矩阵

| 边界 | 可重试 | 不重试 |
|---|---|---|
| DeepSeek 内容 | 空、截断、非法 JSON、模型校验失败，最多两次 | 重试耗尽 |
| DeepSeek HTTP | 由适配器按明确网络策略处理 | 认证、请求合同错误 |
| Suno submit/details | 连接、响应头前断连、429、5xx，总期限内有限 | 4xx 参数/认证、业务失败、未知状态 |
| 知识库 | 不阻断生成，返回通用警告 | 不把内部异常暴露为 API 错误 |
| 媒体 | 传输错误最多三次；耗尽后终止完成流程 | HTTP 状态错误、非 HTTPS、私网、重定向、越界大小 |

## 8. 日志与脱敏

CollaborationLog 不保存 API key、Authorization、reasoning_content、知识 excerpt、绝对路径或完整供应商原始 JSON。Suno URL 删除查询参数；知识只保存引用元数据；API 返回 GenerationRecord.public 视图，不返回 CollaborationLog 全量对象。

## 9. 契约验证

- FastAPI：422、404、409、500、503、202、204、删除状态/路径边界、Range 206/416、下载文件名。
- DeepSeek：JSON 正常/空/截断/非法/校验失败，隐藏推理隔离。
- Suno：所有状态、空候选、未知状态、网络/429/5xx、总超时、停止事件。
- 媒体：来源白名单、HTTPS、公网、重定向、大小、超时、路径遍历和原子替换。
