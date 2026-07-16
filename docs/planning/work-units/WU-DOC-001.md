# WU-DOC-001 文档架构重构实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: 使用 `executing-plans` 按任务顺序实施；每完成一个任务先运行该任务的验证，再进入下一任务。实际状态只写入 `docs/planning/STATUS.md`，本文件按已批准的 WU 规则不使用完成勾选。

**Goal：** 在不丢失现有有效信息的前提下，将 theNanGuos 文档重构为可由项目维护者和 Coding Agent 稳定使用的分层事实源。

**Architecture：** 先以自动化文档合同建立失败基线，再创建目标目录和骨架，按“产品与行为 → 技术专题 → 计划与 WU → Git 边界”迁移内容。旧根目录文档在内容映射、链接检查和一致性检查全部通过前保留；最终删除只通过可审查补丁完成。

**Tech Stack：** Markdown、Mermaid、Python 3.11 标准库、pytest、Git。

**实际状态：** 见 [`STATUS.md`](../STATUS.md)。

---

## 1. WU 合同

| 项目 | 内容 |
|---|---|
| WU ID | `WU-DOC-001` |
| 领域 | `DOC`：文档架构与治理 |
| 所属阶段 | P1 工程基础与配置；同时为 P2–P9 提供事实源 |
| 目标里程碑 | M5 完整验收 |
| 设计事实源 | `docs/planning/designs/2026-07-14-documentation-architecture-design.md` |
| 前置依赖 | 当前根目录 PRD、SPEC、IA、架构、PLAN、STATUS 和代码实现可读取 |
| 后续依赖方 | 所有后续功能 WU、真实供应商联调和视觉验收 |

### 1.1 允许修改范围

- 根目录 `README.md` 和 `.gitignore`；
- 当前根目录正式文档：`PRD.md`、`SPEC.md`、`ARCHITECTURE.md`、`INFORMATION_ARCHITECTURE.md`、`PLAN.md`、`STATUS.md`、`WEB_UI_DESIGN.md`；
- 新目录 `docs/`；
- 文档合同测试 `tests/test_documentation_contract.py`；
- 必要时更新本地 `PROGRESS.md`，但它继续被 Git 忽略。

### 1.2 明确非范围

- 不修改 Python、Vue、LangGraph、DeepSeek 或 Suno 的运行行为；
- 不改变 API、Schema、CLI 或配置合同；
- 不删除 `design/prototypes/` 中已确认的高保真原型；
- 不重新设计 Web UI；
- 不执行真实 DeepSeek 或 Suno 请求；
- 不安装新的 Markdown 工具或第三方依赖；
- 不提交、不推送、不创建 PR，除非用户另行明确授权；
- 不覆盖当前工作树中与本 WU 无关的未提交修改。

## 2. 目标文件与职责

### 2.1 创建

| 文件 | 职责 |
|---|---|
| `docs/README.md` | 文档入口、阅读路径、权威归属表、稳定标识规则 |
| `docs/product/PRD.md` | 产品目标、用户流程、核心对象和业务规则 |
| `docs/product/SPEC.md` | 全部用户可观察功能、状态、异常和验收行为 |
| `docs/product/WEB_UI_DESIGN.md` | 五页信息层级、组件、交互和视觉基线 |
| `docs/architecture/ARCHITECTURE.md` | 系统上下文、组件、部署、工程结构和技术选型 |
| `docs/architecture/INFORMATION_ARCHITECTURE.md` | 信息域、域关系、生命周期和页面信息流 |
| `docs/architecture/AGENT_SYSTEM.md` | Agent、Tool、推理、GraphState、偏好和知识机制 |
| `docs/architecture/DATA_MODEL.md` | 领域模型、字段、约束、JSON 和本地存储映射 |
| `docs/architecture/API_SPEC.md` | FastAPI、DeepSeek、Suno 的协议合同 |
| `docs/planning/PLAN.md` | P1–P9 规范化主路线、Milestone 和 WU 索引 |
| `docs/planning/STATUS.md` | 唯一项目进度与验证证据看板 |
| `tests/test_documentation_contract.py` | 文档存在、职责、图表、链接和迁移边界的自动检查 |

### 2.2 修改

| 文件 | 修改目的 |
|---|---|
| `README.md` | 链接正式文档入口，保留启动和最小验证信息 |
| `.gitignore` | 保持根目录 Markdown 忽略，同时允许 `docs/**/*.md` 跟踪并忽略草稿目录 |
| `docs/planning/designs/2026-07-14-documentation-architecture-design.md` | 迁移完成后只修正实际路径或术语，不扩大设计范围 |

### 2.3 最终移除的根目录副本

以下文件只在新文档内容完整、自动检查通过后通过补丁移除：

- `PRD.md`；
- `SPEC.md`；
- `ARCHITECTURE.md`；
- `INFORMATION_ARCHITECTURE.md`；
- `PLAN.md`；
- `STATUS.md`；
- `WEB_UI_DESIGN.md`。

`PROGRESS.md` 保留在根目录并继续忽略；`README.md` 保留并跟踪。

## 3. 内容迁移矩阵

| 来源章节 | 目标章节 | 迁移要求 |
|---|---|---|
| PRD 1–7 | `docs/product/PRD.md` | 保留定位、目标、非目标、角色、流程和页面级产品要求 |
| PRD 8–10 | PRD 摘要 + `AGENT_SYSTEM.md` | PRD 每类能力不超过职责摘要；机制完整迁入 Agent 专题 |
| PRD 11 | PRD 核心对象词汇 + `DATA_MODEL.md` | PRD 删除完整 JSON；字段、枚举和约束全部迁入数据模型 |
| PRD 12、14 | PRD + SPEC | 产品规则留 PRD；可观察行为和验收场景进入 SPEC |
| PRD 13 | ARCHITECTURE + DATA_MODEL | 工程目录归架构；产物目录和文件格式归数据模型 |
| SPEC 2 | AGENT_SYSTEM + DATA_MODEL | 规划/记忆机制归 Agent；TaskPlan 字段归数据模型 |
| SPEC 2.1 | SPEC + API_SPEC + WEB_UI_DESIGN | 两阶段行为归 SPEC；请求合同归 API；交互归 UI |
| SPEC 2.2 | AGENT_SYSTEM + DATA_MODEL + SPEC | 检索机制归 Agent；知识 Schema 归数据；降级行为归 SPEC |
| SPEC 3–4 | API_SPEC + DATA_MODEL + SPEC | Suno 协议归 API；对象字段归数据；用户可见状态归 SPEC |
| SPEC 5 | SPEC + STATUS 规则 | 验收行为归 SPEC；当前证据不迁入 SPEC |
| IA 2–10 | INFORMATION_ARCHITECTURE | 保留信息域，删除字段重复，补拥有者、读写方和生命周期 |
| IA 11–12 | API_SPEC + SPEC + IA 摘要 | API 形状归 API；状态行为归 SPEC；IA 只保留跨域映射 |
| IA 13 | ARCHITECTURE + AGENT_SYSTEM | 系统安全归架构；prompt/知识隔离归 Agent |
| ARCHITECTURE 1–4 | ARCHITECTURE | 上下文、入口和工程结构保留并改为中文显式树 |
| ARCHITECTURE 5–7 | AGENT_SYSTEM + ARCHITECTURE 摘要 | 图、Agent、记忆细节归 Agent；系统级边界留架构 |
| ARCHITECTURE 8–15 | ARCHITECTURE + API_SPEC | 生命周期、存储、安全、测试归架构；HTTP 合同归 API |
| PLAN 1–18 | `docs/planning/PLAN.md` | 按 P1–P9 重排目标顺序，删除实时状态措辞 |
| PLAN 19 | PLAN P3–P5 + `WU-KNOW-*` | 能力归主路线；实施过程按实际代码证据形成知识 WU |
| STATUS 全文 | `docs/planning/STATUS.md` | 改为 Milestone + WU 看板，保留最新验证证据 |
| WEB_UI_DESIGN 全文 | `docs/product/WEB_UI_DESIGN.md` | 保留原型约束和五页交互，修正新文档相对链接 |

## 4. 实施任务

### Task 1：建立文档合同的失败基线

**文件：**

- 创建：`tests/test_documentation_contract.py`
- 读取：设计文档和当前根目录文档

**Action 1.1：创建目标文档清单测试**

测试定义以下正式文件必须存在：

```python
from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"

REQUIRED_DOCS = [
    DOCS / "README.md",
    DOCS / "product" / "PRD.md",
    DOCS / "product" / "SPEC.md",
    DOCS / "product" / "WEB_UI_DESIGN.md",
    DOCS / "architecture" / "ARCHITECTURE.md",
    DOCS / "architecture" / "INFORMATION_ARCHITECTURE.md",
    DOCS / "architecture" / "AGENT_SYSTEM.md",
    DOCS / "architecture" / "DATA_MODEL.md",
    DOCS / "architecture" / "API_SPEC.md",
    DOCS / "planning" / "PLAN.md",
    DOCS / "planning" / "STATUS.md",
    DOCS / "planning" / "designs" / "2026-07-14-documentation-architecture-design.md",
    DOCS / "planning" / "work-units" / "WU-DOC-001.md",
]


def test_required_documentation_exists() -> None:
    missing = [path.relative_to(ROOT).as_posix() for path in REQUIRED_DOCS if not path.is_file()]
    assert missing == []
```

**Action 1.2：增加职责和迁移边界测试**

在同一测试文件中加入：

```python
LEGACY_ROOT_DOCS = [
    "PRD.md",
    "SPEC.md",
    "ARCHITECTURE.md",
    "INFORMATION_ARCHITECTURE.md",
    "PLAN.md",
    "STATUS.md",
    "WEB_UI_DESIGN.md",
]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_legacy_root_document_copies_are_removed() -> None:
    remaining = [name for name in LEGACY_ROOT_DOCS if (ROOT / name).exists()]
    assert remaining == []


def test_plan_uses_phases_and_work_units_without_progress_checkboxes() -> None:
    plan = read("docs/planning/PLAN.md")
    assert all(f"P{number}" in plan for number in range(1, 10))
    assert "Work Unit" in plan
    assert "阶段 " + "19" not in plan
    assert not re.search(r"^- \[[ xX]\]", plan, flags=re.MULTILINE)


def test_work_unit_delegates_status_to_status_board() -> None:
    work_unit = read("docs/planning/work-units/WU-DOC-001.md")
    assert "实际状态见 `docs/planning/STATUS.md`" in work_unit
    assert not re.search(r"^- \[[ xX]\]", work_unit, flags=re.MULTILINE)
```

执行前需要把本 WU 文件中的执行要求统一为上述精确状态语句。

**Action 1.3：增加图表、功能 ID 和链接测试**

```python
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def test_required_diagrams_exist() -> None:
    architecture = read("docs/architecture/ARCHITECTURE.md")
    information = read("docs/architecture/INFORMATION_ARCHITECTURE.md")
    agents = read("docs/architecture/AGENT_SYSTEM.md")
    data_model = read("docs/architecture/DATA_MODEL.md")
    spec = read("docs/product/SPEC.md")
    assert architecture.count("```mermaid") >= 2
    assert "信息域关系图" in information and "```mermaid" in information
    assert "生成时序图" in agents and "sequenceDiagram" in agents
    assert "核心对象 UML" in data_model and "classDiagram" in data_model
    assert "任务状态机" in spec and "stateDiagram" in spec


def test_spec_uses_stable_function_ids() -> None:
    spec = read("docs/product/SPEC.md")
    assert "FR-PREVIEW-001" in spec
    assert "FR-GEN-001" in spec
    assert "FR-POLL-001" in spec
    assert "FR-PREF-001" in spec


def test_relative_markdown_links_resolve() -> None:
    broken: list[str] = []
    for path in REQUIRED_DOCS:
        text = path.read_text(encoding="utf-8")
        for target in MARKDOWN_LINK.findall(text):
            if target.startswith(("http://", "https://", "#")):
                continue
            file_target = target.split("#", 1)[0]
            if file_target and not (path.parent / file_target).resolve().exists():
                broken.append(f"{path.relative_to(ROOT).as_posix()} -> {target}")
    assert broken == []
```

**Action 1.4：运行失败基线**

运行：

```powershell
uv run pytest tests/test_documentation_contract.py -q
```

预期：失败，至少报告目标正式文档尚未创建、根目录旧副本尚未移除。失败证明合同能够捕获迁移前状态。

### Task 2：建立文档入口和产品层

**文件：**

- 创建：`docs/README.md`
- 创建：`docs/product/PRD.md`
- 创建：`docs/product/SPEC.md`
- 创建：`docs/product/WEB_UI_DESIGN.md`
- 修改：`README.md`

**Action 2.1：创建 docs/README.md**

必须包含：

1. “按目标阅读”表：了解产品、实现功能、修改 Agent、修改数据、修改 API、查看计划、查看状态；
2. 权威归属表：产品、行为、UI、系统、信息、Agent、字段、API、计划、状态；
3. 稳定 ID 规则：`FR-*`、`DM-*`、`API-*`、`WU-*`、`P*`、`M*`；
4. 更新矩阵：变更类型对应必须同步的文档；
5. 明确 `STATUS.md` 是唯一进度源。

**Action 2.2：迁移 PRD**

按以下目录创建 `docs/product/PRD.md`：

```text
1. 文档职责
2. 产品定位
3. 产品目标
4. 非目标
5. 用户与场景
6. 核心用户流程
7. 产品能力
8. 核心对象词汇表
9. 核心业务规则
10. 产品级异常与边界
11. 产品验收标准
12. 相关文档
```

迁移要求：

- 完整保留 Web 和 CLI 主流程；
- Agent、Tool、短期记忆、长期偏好和知识库各保留产品含义与禁止行为；
- 核心对象词汇表只记录对象名、产品含义、生产者、消费者和权威链接；
- 删除全部完整 JSON 代码块；
- 不删除 Suno 封面、停止等待、继续查询、偏好不自动学习等已确认规则。

**Action 2.3：扩展 SPEC**

使用以下功能 ID：

| ID | 功能 |
|---|---|
| `FR-PREVIEW-001` | 生成并确认创作预览 |
| `FR-GEN-001` | 创建歌曲生成任务 |
| `FR-AGENT-001` | 执行四 Agent 创作阶段 |
| `FR-POLL-001` | 轮询 Suno 状态 |
| `FR-WAIT-001` | 停止等待与继续查询 |
| `FR-RESULT-001` | 展示、播放和下载候选歌曲 |
| `FR-WORK-001` | 索引和筛选本地作品 |
| `FR-PREF-001` | 保存和清除确认型偏好 |
| `FR-KNOW-001` | 使用只读创作知识 |
| `FR-CLI-001` | CLI 离线与提交模式 |
| `FR-RESTART-001` | 服务重启后标记中断任务 |

每项严格使用“前置条件、输入摘要、主流程、状态变化、异常与恢复、输出摘要、验收场景、相关合同”八段结构。字段表只提供链接，不复制 API 或 Pydantic 定义。

**Action 2.4：迁移 Web UI 设计**

完整迁移现有五页、显式 demo 开关、高保真原型路径和实质偏离确认规则。把字段类型链接到 DATA_MODEL，把请求行为链接到 API_SPEC。

**Action 2.5：更新根 README 文档入口**

在启动说明之前增加“文档”小节，至少链接：

```markdown
- [文档地图](docs/README.md)
- [产品需求](docs/product/PRD.md)
- [功能规格](docs/product/SPEC.md)
- [系统架构](docs/architecture/ARCHITECTURE.md)
- [实施计划](docs/planning/PLAN.md)
- [开发状态](docs/planning/STATUS.md)
```

**Action 2.6：运行产品层检查**

运行：

```powershell
uv run pytest tests/test_documentation_contract.py -q
```

预期：仍失败，但不再报告 `docs/README.md` 和三份产品层文档缺失；功能 ID 检查通过。

### Task 3：重写系统架构与信息架构

**文件：**

- 创建：`docs/architecture/ARCHITECTURE.md`
- 创建：`docs/architecture/INFORMATION_ARCHITECTURE.md`

**Action 3.1：创建系统上下文图**

ARCHITECTURE 的 Mermaid `flowchart` 必须包含：用户、Vue Web UI、CLI、FastAPI 单进程、DeepSeek、Suno、本地文件系统。图后增加参与者职责表，明确数据方向和信任边界。

**Action 3.2：创建组件图**

第二张 Mermaid 图必须包含：API 路由、PreviewStore、TaskRegistry、GenerateSongGraph、Agent/LLM、PreferenceStore、KnowledgeStore/Retriever、SunoClient、ArtifactStore。图后增加组件职责、输入、输出和依赖表。

**Action 3.3：重写工程结构**

工程树必须基于当前仓库实际路径，使用中文注释和显式树线，例如：

```text
the_nanguos/
├─ api/                 HTTP 路由、请求校验与媒体响应
├─ agents/              四个结构化创作 Agent
├─ graphs/              固定 LangGraph 与单次 GraphState
├─ knowledge/           Markdown 知识加载、索引和检索
├─ llm/                 供应商无关客户端与 DeepSeek 适配
├─ memory/              用户确认型偏好存储
├─ schemas/             领域对象与协议模型
├─ services/            任务、生成、存储和 Suno 服务
└─ tools/               确定性 Suno 请求构造
```

树后逐项列出“模块、职责、主要依赖、对应代码路径”。

**Action 3.4：增加技术选型表**

至少覆盖：Vue 3、Pinia、FastAPI、LangGraph、Pydantic、httpx、Markdown/YAML、pytest、Playwright、单进程、本地文件存储、确定性检索。每项包含需求、选择、理由、暂不选择的替代方案。

**Action 3.5：重写信息架构**

创建信息域关系 Mermaid 图，包含：用户输入域、创作规划域、运行状态域、长期偏好域、创作知识域、外部协议域、本地作品域、页面展示域。

每个域用统一表格记录：目的、核心对象、写入方、读取方、生命周期、持久化位置、字段权威链接。删除完整字段定义副本。

**Action 3.6：增加对象生命周期说明**

用文字时序说明 `UserNaturalLanguage → Preview → SongSpec/TaskPlan → GenerationRecord/GraphState → SunoTaskDetails → Work`，并明确：

- Preview 进程内、30 分钟、一次消费；
- GraphState 不跨进程恢复；
- GenerationRecord 服务进程内运行，重启后从日志重建只读状态；
- Work 使用本地媒体和协作日志长期保存；
- UserProfile 与 StylePreferences 独立于单次生成；
- KnowledgeCatalog 是可重建缓存。

**Action 3.7：运行架构检查**

运行：

```powershell
uv run pytest tests/test_documentation_contract.py::test_required_diagrams_exist -q
```

预期：仍因 Agent、数据和 SPEC 图未齐全而失败；ARCHITECTURE 的两张图和 IA 图已经满足局部合同。

### Task 4：建立 Agent、数据与 API 三份技术专题

**文件：**

- 创建：`docs/architecture/AGENT_SYSTEM.md`
- 创建：`docs/architecture/DATA_MODEL.md`
- 创建：`docs/architecture/API_SPEC.md`

**Action 4.1：编写 AGENT_SYSTEM.md**

目录固定为：

```text
1. 文档职责与边界
2. 设计目标
3. 固定 LangGraph
4. 四个 Agent
5. 确定性 Tool
6. 推理与结构化输出
7. 短期记忆 GraphState
8. 用户长期偏好
9. 创作知识库
10. 两阶段检索与职责视图
11. 生成时序图
12. 降级、日志和安全
13. 测试合同
```

生成时序图使用 Mermaid `sequenceDiagram`，参与者至少包含 Browser、FastAPI、Conductor、KnowledgeRetriever、Lyrics、MusicPlanner、Arrangement、SunoClient、ArtifactStore。明确预览阶段只调用一次 Conductor，正式生成复用确认结果。

四个 Agent 表格必须记录输入、输出、知识视图、允许行为、禁止行为；Suno builder 明确不能直接访问知识库，Lyrics 明确不能取得经典曲目分析。

**Action 4.2：编写 DATA_MODEL.md**

对象至少覆盖：

- TaskPlan、TaskStep；
- SongSpec 及嵌套对象；
- LyricsResult、MusicPlanResult、ArrangementResult；
- ScorePlan；
- GenerationPreview、GenerationRecord、GraphState；
- SunoRequest、SunoTaskDetails、SunoAudio；
- CollaborationLog、KnowledgeLog；
- UserProfile、StylePreferences；
- KnowledgeDocument、KnowledgeCatalog、KnowledgeQuery、KnowledgeContext、AgentKnowledgeView；
- Work 和本地媒体元数据。

核心对象 UML 使用 Mermaid `classDiagram`。每个对象以 `DM-<ObjectName>` 为稳定 ID，并从当前 Pydantic/Dataclass/TypedDict 实现提取字段；不得凭设计文档新增代码中不存在的字段。对设计合同存在但代码尚未实现的对象，显式标记“协议视图”或“UI 视图”，不能写成 Pydantic 实体。

**Action 4.3：编写 API_SPEC.md**

本地接口完整列出：

```text
POST   /api/generation-previews
POST   /api/generations
GET    /api/generations
GET    /api/generations/{request_id}
POST   /api/generations/{request_id}/stop-waiting
POST   /api/generations/{request_id}/resume-polling
GET    /api/generations/{request_id}/audio/{audio_id}
GET    /api/generations/{request_id}/audio/{audio_id}/download
GET    /api/generations/{request_id}/cover/{audio_id}
GET    /api/preferences
PUT    /api/preferences/defaults
PUT    /api/preferences/style
DELETE /api/preferences
```

必须从当前 `the_nanguos/api/app.py` 验证实际路径和状态码；如代码与旧文档冲突，以代码与测试为实现证据，并在文档中区分“当前实现”和“目标合同”。

DeepSeek 合同记录 JSON Output、Thinking Mode、最终 `content`、两次重试、禁止记录 `reasoning_content`。Suno 合同完整保留生成、详情查询、状态分类、轮询、字段限制、媒体 HTTPS 和错误重试边界。

**Action 4.4：运行技术专题检查**

运行：

```powershell
uv run pytest tests/test_documentation_contract.py::test_required_diagrams_exist -q
```

预期：通过。

### Task 5：重构 PLAN、STATUS 和 WU 体系

**文件：**

- 创建：`docs/planning/PLAN.md`
- 创建：`docs/planning/STATUS.md`
- 修改：`docs/planning/work-units/WU-DOC-001.md`
- 创建：必要的 `docs/planning/work-units/WU-<AREA>-<NNN>.md`

**Action 5.1：编写 PLAN.md**

结构固定为：

```text
1. 文档职责
2. 目标系统与完成定义
3. Phase P1–P9
4. Phase 依赖图
5. Milestone M1–M5
6. WU 编号与拆分规则
7. WU 索引
8. 风险与非目标
```

知识库能力按逻辑归入：

- P3：偏好文件、知识 Markdown、Store、Catalog、Retriever；
- P4：Agent 职责视图和 prompt 注入；
- P5：两阶段检索节点、GraphState 上下文和降级日志。

PLAN 不出现完成勾选、测试通过数量、当前日期状态或“第 19 点”。

**Action 5.2：定义 WU 索引**

根据当前代码和测试证据建立最少集合，不为历史细节虚构大量 WU。初始建议：

| WU | 结果 |
|---|---|
| `WU-CORE-001` | Python/Vue 工程、配置和入口 |
| `WU-DATA-001` | 核心 Schema 与字段合同 |
| `WU-AGENT-001` | DeepSeek 结构化输出和四 Agent |
| `WU-KNOW-001` | 偏好、知识 Schema、Store 和样例 |
| `WU-KNOW-002` | 检索、Agent 视图、日志和安全边界 |
| `WU-GRAPH-001` | 固定 LangGraph 和离线产物 |
| `WU-SUNO-001` | Suno 请求、轮询和媒体保存 |
| `WU-API-001` | FastAPI、任务注册表和媒体接口 |
| `WU-WEB-001` | 五页 Web UI 和播放器 |
| `WU-QA-001` | Mock 全栈 E2E 和构建验收 |
| `WU-DOC-001` | 文档架构重构 |

只有需要详细交接或后续修改的 WU 才创建独立文件；PLAN 索引可以先登记其余 WU，避免为已完成历史制造空洞文档。

**Action 5.3：编写 STATUS.md**

结构固定为：

```text
1. 当前结论
2. Milestone 看板
3. 当前 WU
4. WU 看板
5. 最新验证证据
6. 阻塞与风险
7. 下一开发顺序
8. 看板维护规则
```

状态映射：

| 状态 | 中文 | 含义 |
|---|---|---|
| planned | 已规划 | 范围存在但依赖未满足 |
| ready | 可开始 | 设计与依赖已满足 |
| in_progress | 进行中 | 当前正在实施 |
| blocked | 阻塞 | 缺少外部条件且无法继续 |
| done | 已完成 | 产物和验证证据齐全 |

迁移当前新鲜证据：后端 91 passed、前端 20 passed、E2E 3 passed、类型检查和构建通过；真实 DeepSeek 与 Suno 未联调。执行时必须重新运行验证并用新结果替换，不能直接把旧数字当成当前证据。

**Action 5.4：统一 WU 状态语句**

本文件和以后所有 WU 使用精确文本：

```markdown
**实际状态：** 见 [`STATUS.md`](../STATUS.md)。
```

随后同步调整文档合同测试，使其检查该链接和文本，而不是保存任何状态值。

**Action 5.5：运行计划合同**

运行：

```powershell
uv run pytest tests/test_documentation_contract.py::test_plan_uses_phases_and_work_units_without_progress_checkboxes tests/test_documentation_contract.py::test_work_unit_delegates_status_to_status_board -q
```

预期：2 passed。

### Task 6：切换 Git 边界并移除旧副本

**文件：**

- 修改：`.gitignore`
- 删除：七份已迁移根目录正式文档
- 保留：`README.md`、`PROGRESS.md`

**Action 6.1：检查迁移完整性**

在删除前运行：

```powershell
uv run pytest tests/test_documentation_contract.py -q
```

预期：唯一允许的失败是旧根目录副本仍存在。若存在其他失败，不得删除旧文档。

**Action 6.2：调整 .gitignore**

目标规则必须表达：

```gitignore
# 根目录本地文档；正式文档位于 docs/
/*.md
!/README.md

# 本地过程与草稿
/PROGRESS.md
/docs/_drafts/
```

`/*.md` 不匹配 `docs/**/*.md`，不得增加 `/docs/` 或 `docs/**/*.md` 忽略规则。

**Action 6.3：通过 apply_patch 移除旧副本**

仅在 Action 6.1 达到预期后，使用 `apply_patch` 删除七份根目录副本；不使用 `Remove-Item`、`git clean` 或其他批量删除命令。

**Action 6.4：验证 Git 边界**

运行：

```powershell
git check-ignore -v PROGRESS.md
git check-ignore -v docs/product/PRD.md
git status --short docs README.md .gitignore
```

预期：

- `PROGRESS.md` 显示被根目录 Markdown 规则忽略；
- `docs/product/PRD.md` 命令返回非零且无输出，表示未被忽略；
- `git status` 显示 `docs/` 中正式文档可跟踪；
- 根目录旧文档显示删除或因原本未跟踪而不再存在。

### Task 7：全量一致性审查和验证

**文件：**

- 可能修改：所有本 WU 新建正式文档，仅修正审查发现的问题
- 更新：本地 `PROGRESS.md`

**Action 7.1：运行完整文档合同**

```powershell
uv run pytest tests/test_documentation_contract.py -q
```

预期：全部通过。

**Action 7.2：扫描占位和旧路径**

```powershell
$forbidden = @('未完成' + '标记', '阶段 ' + '19', '\]\((\.\./){2,}(PRD|SPEC|ARCHITECTURE|PLAN|STATUS)\.md')
Get-ChildItem docs -Recurse -File -Filter *.md |
  Select-String -Pattern ($forbidden -join '|') -CaseSensitive:$false
```

预期：无输出。若设计文档需要讨论这些字面量，应改写为不触发正式文档扫描的表达。

**Action 7.3：核对实现事实**

使用 PowerShell 搜索并逐项比对：

```powershell
Get-ChildItem the_nanguos,frontend/src,tests -Recurse -File -Include *.py,*.ts,*.vue |
  Select-String -Pattern 'generation-previews|stop-waiting|resume-polling|FIRST_SUCCESS|service_restarted|KnowledgeContext|deepseek-v4-pro'
```

预期：文档中的接口、状态、模型名和知识对象均能追溯到代码或测试；设计合同但未实现的内容必须明确标记为待验证能力。

**Action 7.4：运行全量项目验证**

依次运行：

```powershell
uv run pytest -q
```

```powershell
Set-Location frontend
npm test -- --run
npm run typecheck
npm run build
npm run test:e2e
```

预期：

- 后端与文档合同测试全部通过；
- 前端单元测试通过；
- 类型检查通过；
- 生产构建通过；
- Chromium E2E 通过。

不得预先写死最终测试数量；以执行时新鲜输出更新 STATUS。

**Action 7.5：检查补丁质量**

```powershell
Set-Location ..
git diff --check
git status --short
```

预期：`git diff --check` 无错误；`git status` 只包含本 WU 文档迁移和执行前已有的用户修改，不出现凭据、缓存、构建产物或可视化伴侣文件。

**Action 7.6：记录经验教训**

在本地 `PROGRESS.md` 追加：问题、重构方式、防止重复定义的规则、验证结果和“未提交”或用户之后授权产生的 commit ID。

## 5. 完成标准

WU-DOC-001 只有同时满足以下条件才可在 STATUS 标为 done：

1. 设计文档中定义的目标目录全部存在；
2. 当前有效内容均能从迁移矩阵定位到正式文档；
3. PRD 不包含字段级完整 JSON；
4. SPEC 覆盖所有用户可观察功能和异常行为；
5. AGENT_SYSTEM、DATA_MODEL、API_SPEC 分别成为机制、字段和协议的唯一详细来源；
6. IA 和系统架构补齐六类正式图中属于各自职责的图；
7. 系统架构工程树使用中文注释、显式结构线和职责表；
8. PLAN 使用 P1–P9 和领域 WU，不再包含第 19 点或实时状态；
9. STATUS 是唯一进度看板，并使用新鲜验证证据；
10. WU 文件不保存状态值或完成勾选；
11. 正式 docs 纳入 Git，临时草稿、PROGRESS 和凭据继续忽略；
12. 所有相对链接有效，文档合同测试通过；
13. 全量后端、前端、构建和浏览器 E2E 通过；
14. 未发生代码行为、API、Schema 或 UI 视觉变更；
15. 用户已有未提交工作未被覆盖或回滚。

## 6. 风险与回滚边界

### 6.1 信息丢失

控制：旧根目录文档保留到 Task 6；Task 2–5 逐项使用迁移矩阵。发现缺失时只补新文档，不提前删除来源。

### 6.2 正式文档与代码冲突

控制：字段、接口和状态以当前代码与测试作为“已实现”证据；设计文档只作为目标边界。冲突不能静默选择，必须在新文档中注明当前实现和目标合同，必要时暂停并请用户决定是否另建代码 WU。

### 6.3 迁移扩大到代码重构

控制：本 WU 禁止修改运行时代码。发现文档无法描述的代码缺陷时记录为独立候选 WU，不在 WU-DOC-001 中顺带修复。

### 6.4 Git 跟踪范围扩大

控制：只让 `docs/**/*.md` 成为新的正式跟踪范围。不得提交 `.env`、outputs、缓存、可视化会话或本地 PROGRESS。

### 6.5 回滚

迁移未完成时，保留根目录来源文档即可回退阅读入口。最终移除来源后，如需恢复，只能在用户明确授权的 Git 操作中从历史恢复；禁止使用会覆盖工作树的破坏性命令。

## 7. 交接要求

执行完成后的交接必须包含：

1. 新文档地图；
2. 被迁移和移除的根目录文件；
3. 文档合同测试结果；
4. 全量后端、前端、构建和 E2E 结果；
5. 未解决的代码/文档差异；
6. Git 忽略与跟踪边界；
7. 未提交、未推送的明确说明，除非用户另行授权；
8. STATUS 中 WU-DOC-001 的状态与证据位置。
