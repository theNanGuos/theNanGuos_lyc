# theNanGuos 开发状态

> 本文件是项目进度、阻塞、下一步和验证证据的唯一看板。PLAN 和 WU 只定义目标与任务合同，不记录完成状态。

最后更新：2026-07-15

## 1. 当前结论

MVP 的 M1–M6 均已达到当前计划的验收门槛。M6 已完成创作/等待页修正、默认本地保留 1 个候选、真实播放进度、候选独立音量、复用结果页选择版本，以及二次确认删除整次生成任务。供应商 payload 与计费语义未变化；新增行为已通过后端、前端、Chromium、视觉、安全与文档验收。

## 2. Milestone 看板

| Milestone | 状态 | 证据摘要 | 剩余条件 |
|---|---|---|---|
| M1 本地结构化产物 | done（已完成） | 真实 DeepSeek 四 Agent `--no-submit` 生成四个 JSON，Pydantic 4/4 通过且无 Suno taskId | 无 |
| M2 Mock 全栈闭环 | done（已完成） | FastAPI + Vite + Mock 供应商 Chromium 主流程/停止继续/偏好闭环 | 无 |
| M3 真实 DeepSeek | done（已完成） | Thinking Mode + JSON Output 最小请求及四 Agent 链路成功；推理/凭据未进入产物 | 无 |
| M4 真实 Kie.ai Suno | done（已完成） | 单次真实提交成功轮询出 2 首歌曲，MP3/封面落盘及本地详情、Range、封面、下载接口均通过 | 无 |
| M5 完整验收 | done（已完成） | 两个真实供应商、重启后浏览器场景、五页视觉、可访问性、安全清单和全量自动化均有证据 | 无 |
| M6 交互与作品管理增强 | done（已完成） | 五个 WU 完成；本地候选审计、时间进度/独立音量、版本入口、整任务删除、1440×1024 与 Chromium 闭环均通过 | 无 |

## 3. 当前 WU

当前无进行中的功能 WU；最近完成 `WU-QA-002`，M6 已综合验收。

- 最近完成：`WU-QA-002` M6 综合验收。
- 已具备：Mock 全栈、两个真实供应商、重启后继续查询、五页截图、关键可访问性、最终安全清单、知识安全和文档合同证据。
- 外部条件：无；后续若需要改变导航、主要 CTA、字段分组或整体视觉语言，仍须先由用户确认更新原型。

## 4. WU 看板

| WU | 状态 | 主要证据/说明 |
|---|---|---|
| WU-CORE-001 | done（已完成） | uv/Vue/FastAPI/CLI 工程和入口存在 |
| WU-DATA-001 | done（已完成） | Schema 与合同测试覆盖核心对象和 Suno |
| WU-KNOW-001 | done（已完成） | 偏好、知识模型、Store、三类人工样例 |
| WU-AGENT-001 | done（已完成） | DeepSeek Mock + 真实 Thinking/JSON Output、结构化 Agent 和四结果模型 |
| WU-KNOW-002 | done（已完成） | 两阶段检索、职责视图、降级、脱敏日志、符号链接边界 |
| WU-GRAPH-001 | done（已完成） | 固定 LangGraph、GraphState、真实四 Agent 离线产物和恢复入口 |
| WU-SUNO-001 | done（已完成） | Kie.ai 请求合同与真实单次提交/轮询验证；2 个候选 MP3/封面本地保存并通过媒体 API 验收 |
| WU-API-001 | done（已完成） | 预览、任务、停止继续、Range/下载、启动索引；interrupted → resume 有浏览器证据 |
| WU-WEB-001 | done（已完成 Mock） | 五页 Vue、Pinia/API、播放器和五个浏览器 E2E |
| WU-QA-001 | done（已完成） | 两个真实供应商、重启恢复、五页视觉基线、关键可访问性、最终安全清单和全量回归均已确认 |
| WU-CONFIG-001 | done（已完成） | CLI/FastAPI 自动向上查找 `.env`，进程环境优先，缺少 DeepSeek 配置返回安全 503；4 项配置回归通过 |
| [WU-DOC-001](work-units/WU-DOC-001.md) | done（已完成） | 正式文档分层、六类图、P1–P9、领域 WU、唯一状态看板和文档合同测试 |
| [WU-WEB-002](work-units/WU-WEB-002.md) | done（已完成） | 空输入与 placeholder、旧 preview 清理、ArrowPath 重试图标、六步稳定网格、删除等待装饰条和外层焦点提示；前端 24 passed、类型/构建通过、E2E 5 passed、1440×1024 视觉复核通过 |
| [WU-SUNO-002](work-units/WU-SUNO-002.md) | done（已完成） | `retention_limit` 严格 1/2/null、默认 1；完整校验后裁剪，日志计数且未保留 URL 不落盘，Kie payload 不变 |
| [WU-WEB-003](work-units/WU-WEB-003.md) | done（已完成） | TrackProgress 绑定真实媒体时间、候选独立音量、作品页复用结果页选择和下载版本 |
| [WU-API-002](work-units/WU-API-002.md) | done（已完成） | 终态整 generation 物理删除、运行中 409、直属目录/符号链接边界、确认弹窗和播放器清理 |
| [WU-QA-002](work-units/WU-QA-002.md) | done（已完成） | 后端 131、前端 32、类型/构建、Chromium 6、1440×1024、文档与安全验收通过 |

## 5. 最新验证证据

M6 当前实现证据：

- 候选保留：API 顶层 `retention_limit` 严格接受 1、2、null，缺省 1；供应商全候选先校验，再按响应顺序截取。下载、公开 candidates、audio_results 和 local_media 只含保留项；日志记录 provider_candidate_count、retention_limit、retained_candidate_count，未保留 URL 有负向测试。
- 播放与版本：TrackProgress 使用 currentTime/duration，支持原生 pointer/keyboard seek；volumeByAudioId 默认 0.75，两个候选互不联动；作品标题、封面和“查看 N 个版本”进入既有结果页，作品行不固定下载首候选。
- 删除：`DELETE /api/generations/{request_id}` 对 completed/failed/stopped/interrupted 返回 204，对 queued/running 返回 409；文件成功后才移除注册表；非法 ID、越界、根目录、符号链接和文件失败均有确定性边界。
- 浏览器：Mock 全栈覆盖创建、停止/继续、重启恢复、偏好、可访问播放、独立音量、版本导航和永久删除；E2E 固定使用独立 15173/18000 测试端口，不复用用户当前 5173/8000 服务。
- 视觉：`design/qa/01-create-preview-m6-final.png`、`03-result-m6.png`、`04-works-m6.png`、`04-works-delete-m6.png` 均为 1440×1024 Chromium 截图；01、03、04 已同步为正式原型基线。
- 后端全量：`uv run pytest -q`，131 passed，2 warnings。
- 前端全量：`npm test -- --run`，32 passed；`npm run typecheck`、`npm run build` 通过。
- Chromium E2E：`npm run test:e2e`，6 passed。

Kie.ai 真实联调与迁移完成后的验证证据：

- 真实 Kie：仅提交 1 个 V4 纯音乐任务，轮询 `SUCCESS`，返回 2 个候选；2 个 MP3 与 2 张 JPEG 封面完整保存至 `outputs/kie-smoke-20260715T090956Z/`。
- 本地真实作品 API：详情 200/`completed`/2 candidates，音频 Range 206/100 bytes，封面 200 `image/jpeg`，下载 200 且 `Content-Disposition` 为 MP3。
- 真实响应兼容回归：进行中不完整候选、source 系列 URL、epoch 毫秒 createTime、响应头前断连和媒体传输重试均有自动化测试。

DeepSeek、重启恢复和视觉验收证据：

- 真实 DeepSeek：单次最小严格 JSON 返回 `ok`；随后四 Agent `--no-submit` 于 `outputs/deepseek-smoke-20260715T093217Z/` 生成 song_spec、score_plan、suno_request、collaboration_log。
- 产物边界：Pydantic 4/4 通过；未出现 reasoning_content、Authorization 或密钥标识；`suno.submitted=false` 且无 taskId。
- 服务重启后交互：Playwright 从磁盘 PENDING 日志经生产 reindex 得到 interrupted，作品页显示“服务已重启，需继续查询”，点击后恢复为已完成。
- 五页视觉：1440 × 1024 Chromium 同状态截图已重拍，审查见 `design/qa/2026-07-15-visual-audit.md`；用户确认当前两阶段创作流程及无“更多”菜单结果页为正式原型基线。
- 可访问性：结果页与作品页图标播放控件均有可读名称，结果页音量滑块有标签，等待页阶段变化使用 polite live region；创作输入和偏好 Markdown 编辑器的键盘焦点环已由 Chromium 验证。
- 配置启动：从未设置 `DEEPSEEK_API_KEY` 的子进程直接导入 FastAPI，确认最近上级 `.env` 被加载；CLI 在启动 Uvicorn 前加载配置；显式进程环境不被覆盖；缺少密钥返回脱敏 503。

- M5 基线后端全量记录：`uv run pytest -q`，112 项测试全部通过，2 warnings；已由上方 M6 的 131 passed 取代。
- Kie/Suno、Schema、生成链路和合同加固目标回归：41 passed。
- M5 基线前端单元记录：`npm test -- --run`，21 passed；已由上方 M6 的 32 passed 取代。
- 前端类型检查：`npm run typecheck`，通过。
- 前端生产构建：`npm run build`，通过。
- M5 基线 Chromium E2E 记录：5 passed；已由上方 M6 的 6 passed 取代。

已知警告：Starlette TestClient/httpx 弃用提示；LangGraph serializer 默认值未来变更提示。

## 6. 最终安全清单

- 本地边界：CLI 固定监听 `127.0.0.1:8000`；CORS 仅允许本地 Vite 两个来源。当前版本无认证，不得直接暴露到公网。
- 凭据边界：`.env` 被忽略且没有被 Git 跟踪；启动时自动加载但不覆盖显式进程环境；对源代码、测试、正式文档和知识库的密钥形态扫描为 0 个可疑文件。
- LLM 边界：只解析最终 `content`；`reasoning_content` 不绑定、不返回、不写产物，并有空内容重试和隔离测试。
- API 与日志：前端只取得公开 GenerationRecord 视图；协作日志不保存密钥、Authorization、完整供应商响应、知识正文或绝对路径。
- 媒体与文件：只接受经任务元数据记录的 HTTPS 公网 URL，拒绝 localhost/私网/重定向，限制大小和超时并使用原子替换；下载文件名经过净化，媒体由 request_id/audio_id 元数据定位。
- 用户内容：Markdown 预览不执行嵌入 HTML；偏好采用原子写入；知识文件拒绝越出根目录的路径和符号链接。
- 回归证据：后端 `131 passed`；前端单元 `32 passed`、类型检查和生产构建通过；Chromium E2E `6 passed`；文档合同包含在后端全量中；`git diff --check` 无空白错误。

## 7. 阻塞与风险

- 真实 Kie 联调发现的进行中不完整候选、source URL、epoch 毫秒时间戳和偶发响应头前断连已兼容；其他供应商未记录字段仍按严格协议错误处理。
- 重启场景通过测试入口写入磁盘日志并调用生产 reindex，验证的是重启后产品状态与交互；没有在测试中真实杀死并重启托管后端进程。
- 当前自动化覆盖焦点可见性、关键图标名称和阶段 live region，但不等同于完整人工屏幕阅读器或全量 WCAG 审计。
- DNS 预解析与媒体实际连接之间仍存在理论上的 DNS rebinding TOCTOU 风险。
- 当前工作树包含一批此前未提交实现；后续开发不得覆盖这些改动。
- Kie/Suno 决定实际候选数量；M6 的 `retention_limit` 只控制本地保存，默认保留第一个候选可能丢弃用户更喜欢的后续变体，且不会降低供应商费用。
- 整任务删除没有回收站；stopped/interrupted 删除后也失去继续查询所需本地 taskId，必须使用增强确认文案并验证路径边界。
- 播放进度只来自本地音频时间，不代表供应商生成进度或真实音频振幅。

## 8. 下一开发顺序

1. 由用户决定下一项产品能力；新增较大功能先建立新 WU，并在本看板登记状态。
2. 若计划公网部署，必须先增加认证、授权、CSRF/限流、可信反向代理和更强的网络出口控制，不能沿用当前本地单用户安全边界。

## 9. 看板维护规则

- 状态只使用：planned（已规划）、ready（可开始）、in_progress（进行中）、blocked（阻塞）、done（已完成）。
- done 必须同时有产物和当前仓库中的验证证据。
- Mock、浏览器、视觉和真实供应商证据分开记录。
- WU 或 PLAN 不保存完成勾选、当前测试数量或状态值。
- 每次完成 WU 后更新本文件的证据、风险和下一步。
