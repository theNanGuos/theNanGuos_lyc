# theNanGuos（南郭先生们）

本项目是一个本地单用户音乐生成 Web 应用：后端通过 LangGraph 编排 DeepSeek，并通过 Kie.ai 调用 Suno 音乐生成能力；前端提供创作、等待、结果、作品和偏好设置五个页面。

歌曲封面直接使用 Suno 音乐生成详情返回的 `imageUrl`，不依赖 DeepSeek 生图。等待页轮询 Suno 的 `PENDING`、`TEXT_SUCCESS`、`FIRST_SUCCESS` 和 `SUCCESS` 状态；百分比是阶段区间内的预计进度，状态文字才是实际生成依据。

## 文档

- [文档地图](docs/README.md)
- [产品需求](docs/product/PRD.md)
- [功能规格](docs/product/SPEC.md)
- [系统架构](docs/architecture/ARCHITECTURE.md)
- [实施计划](docs/planning/PLAN.md)
- [开发状态](docs/planning/STATUS.md)

## 本地启动

要求 Python 3.11+、[uv](https://docs.astral.sh/uv/) 和 Node.js 20+。

```powershell
uv sync --extra dev
Copy-Item .env.example .env
# 编辑 .env，填写 DEEPSEEK_API_KEY 和 KIE_API_KEY
uv run python -m the_nanguos --api
```

另开终端启动前端：

```powershell
Set-Location frontend
npm install
npm run dev
```

浏览器访问 `http://127.0.0.1:5173/`。后端默认监听 `127.0.0.1:8000`。

Kie.ai 要求请求携带 `callBackUrl`。本项目固定以每 30 秒轮询作为结果来源；没有公网回调服务时，使用 `.invalid` 保留域名作为占位地址，不要填写无关的真实网站。Kie 回调投递失败不会替代本地轮询。旧 `SUNO_API_KEY`、`SUNO_BASE_URL` 和 `SUNO_CALLBACK_URL` 暂时兼容，但新配置优先。

## CLI 与检查

```powershell
uv run python -m the_nanguos --help
uv run pytest
Set-Location frontend
npm test
npx playwright install chromium
npm run test:e2e
npm run typecheck
npm run build
```

浏览器 E2E 会自动启动 Vite 和注入 Mock Agent/Suno 的 FastAPI 测试服务，使用系统临时目录保存测试媒体，不需要供应商密钥。

## 创作知识库

人工知识条目分别保存在 `knowledge/styles/`、`knowledge/instruments/` 和 `knowledge/tracks/`。每个文件由 YAML frontmatter 和 Markdown 正文组成；必须提供稳定 ID、类型、名称、别名、标签、至少一个 HTTP(S) 来源和人工复核日期。经典曲目只能记录元数据与抽象的风格、结构、配器和制作经验，不能收录歌词、音频、逐音符旋律或直接模仿指令。

运行以下命令校验三类条目、唯一 ID、目录类型、交叉引用和来源：

```powershell
uv run pytest tests/test_knowledge_models.py tests/test_knowledge_store.py tests/test_knowledge_examples.py -q
```

`knowledge/_index/catalog.json` 是自动生成且被 Git 忽略的派生索引。源文件集合、大小或修改时间变化后，下一次读取会自动刷新索引；Markdown 始终是事实源，Agent 和生成流程不会写回知识条目。

真实生成前必须配置 DeepSeek 与 Kie.ai 密钥。应用启动时会从当前目录向上查找最近的 `.env` 并自动加载；PowerShell 或系统中已经设置的同名环境变量优先，不会被 `.env` 覆盖。`.env.example` 提供变量名参考；`.env`、运行时偏好和作品媒体不会进入版本控制。
