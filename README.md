# theNanGuos（南郭先生们）

本项目是一个本地单用户音乐生成 Web 应用：后端通过 LangGraph 编排 DeepSeek 与 Suno，前端提供创作、等待、结果、作品和偏好设置五个页面。

歌曲封面直接使用 Suno 音乐生成详情返回的 `imageUrl`，不依赖 DeepSeek 生图。等待页轮询 Suno 的 `PENDING`、`TEXT_SUCCESS`、`FIRST_SUCCESS` 和 `SUCCESS` 状态；百分比是阶段区间内的预计进度，状态文字才是实际生成依据。

## 本地启动

要求 Python 3.11+、[uv](https://docs.astral.sh/uv/) 和 Node.js 20+。

```powershell
uv sync --extra dev
$env:DEEPSEEK_API_KEY="your-deepseek-key"
$env:SUNO_API_KEY="your-suno-key"
$env:SUNO_CALLBACK_URL="https://example.com/callback"
uv run python -m the_nanguos --api
```

另开终端启动前端：

```powershell
Set-Location frontend
npm install
npm run dev
```

浏览器访问 `http://127.0.0.1:5173/`。后端默认监听 `127.0.0.1:8000`。

## CLI 与检查

```powershell
uv run python -m the_nanguos --help
uv run pytest
Set-Location frontend
npm test
npm run typecheck
npm run build
```

真实生成前必须在启动后端的进程环境中配置 DeepSeek 与 Suno 密钥；`.env.example` 提供变量名参考，应用当前不会自动加载 `.env`。`.env`、运行时偏好和作品媒体不会进入版本控制。
