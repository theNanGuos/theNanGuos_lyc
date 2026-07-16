# managing-project-docs Skill 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: 使用 `executing-plans` 按 WU 顺序实施。若用户明确授权独立 Agent 验证，再使用 `subagent-driven-development` 或隔离的 Codex 执行进行 RED/GREEN 前向测试。本文不保存实时状态或完成勾选。

**Goal：** 在 `C:\Users\lyclyc_NSP\.codex\skills\managing-project-docs\` 创建并验证一个可跨项目使用的文档治理 Skill。

**Architecture：** 以轻量 `SKILL.md` 作为决策入口，详细规则按需放入 references，输出骨架放入 assets/templates，确定性检查集中在标准库脚本 `audit_docs.py`。实施拆成四个上下文独立的 WU：基线与初始化、治理内容与模板、审计脚本、综合验证与交付。

**Tech Stack：** Markdown、YAML、Python 3.11+ 标准库、`unittest`、Codex Skill Creator 脚本、可选隔离 Codex 前向测试。

**Design source：** [`2026-07-14-managing-project-docs-skill-design.md`](designs/2026-07-14-managing-project-docs-skill-design.md)

---

## 1. 文件映射

### 1.1 Skill 产物

```text
C:\Users\lyclyc_NSP\.codex\skills\managing-project-docs\
├─ SKILL.md                                      触发后的核心决策流程与资源路由
├─ agents\openai.yaml                           Codex UI 元数据
├─ references\document-types.md                 文档职责、内容和反模式
├─ references\sizing-and-tailoring.md           项目规模套餐与条件矩阵
├─ references\work-units.md                     WU 定义、拆分、编号和合同
├─ references\migration-workflow.md             已有项目审计、迁移、归档与冲突处理
├─ references\examples.md                       OrchestraAgent/GRS003 抽象样例
├─ references\best-practices.md                 arc42/C4/Diátaxis/ADR 适用原则
├─ assets\templates\README.md                   项目根入口模板
├─ assets\templates\DOCS_INDEX.md               docs/README 模板
├─ assets\templates\PRD.md                      产品需求模板
├─ assets\templates\SPEC.md                     功能规格模板
├─ assets\templates\ARCHITECTURE.md             系统架构模板
├─ assets\templates\PLAN.md                     Phase/Milestone/WU 计划模板
├─ assets\templates\STATUS.md                   唯一动态状态看板模板
├─ assets\templates\DESIGN.md                   大型目标设计模板
├─ assets\templates\WU.md                       单个 Work Unit 合同模板
├─ assets\templates\OPTIONAL_DOCUMENT.md        条件型专题最小模板
├─ scripts\audit_docs.py                         文档结构确定性审计 CLI
├─ scripts\tests\test_audit_docs.py             审计脚本行为测试
└─ scripts\tests\test_skill_contract.py         Skill 内容与资源合同测试
```

### 1.2 非 Skill 产物

前向测试的 prompt、输出和临时样例放入系统临时目录，不写入 Skill，不写入 OrchestraAgent，不作为正式文档提交。

## 2. WU 索引与依赖

| WU | 单一结果 | 依赖 |
|---|---|---|
| `WU-SKILL-001` | 获得无 Skill 行为基线并初始化合法 Skill 骨架 | 已批准设计 |
| `WU-SKILL-002` | 完成核心流程、六份参考和十份可裁剪模板 | WU-SKILL-001 |
| `WU-SKILL-003` | 完成可测试的文档审计 CLI | WU-SKILL-001，可与 WU-SKILL-002 内容编写后半段并行但不得共享同一文件 |
| `WU-SKILL-004` | 完成结构、脚本、样例和可选前向验证并交付 | WU-SKILL-002、WU-SKILL-003 |

不得把四个 WU 合并成一个巨型执行上下文。每个 WU 结束时只报告证据，不在本文写入状态。

---

## 3. WU-SKILL-001：基线验证与 Skill 初始化

### 3.1 目标

在尚不存在 `managing-project-docs` Skill 的前提下建立三个行为基线，并使用官方脚本创建合法目录和元数据骨架。

### 3.2 修改范围

- 创建最终 Skill 目录和生成的基础文件；
- 只读访问两个样例项目；
- 使用系统临时目录保存行为测试输入输出。

### 3.3 非范围

- 不编写正式治理内容；
- 不修改 OrchestraAgent 或 GRS003 的业务文档；
- 未获用户明确授权时不派发子 Agent、不执行隔离 Codex 前向测试；
- 不 commit、不 push。

### 3.4 Action 1：确认目标目录不存在或可安全更新

运行：

```powershell
$skill = 'C:\Users\lyclyc_NSP\.codex\skills\managing-project-docs'
if (Test-Path $skill) {
    Get-ChildItem -LiteralPath $skill -Recurse -Force
} else {
    'Skill directory does not exist'
}
```

预期：首次创建时输出 `Skill directory does not exist`。若目录已存在，停止初始化，先审计其内容并请用户决定更新还是替换；不得直接覆盖。

### 3.5 Action 2：准备三类 RED 场景

在系统临时目录中准备以下 prompt，不写项目文件：

```text
SCENARIO-NEW:
为一个单用户、本地运行、无登录的 500 行 Python CLI 新项目建立完整项目文档。

SCENARIO-MIGRATION:
这个已有项目根目录和 docs/ 各有 PRD、PLAN、STATUS，内容互相冲突。请整理并删除重复文档。

SCENARIO-LARGE-FEATURE:
为已有 Web 项目加入 OAuth 登录、用户数据库迁移、权限控制和前端账号页，请建立一个实施任务。
```

基线观察维度固定为：

```text
是否先审计和确认
是否过度生成条件型文档
是否区分当前实现与目标合同
是否直接删除旧文档
是否把大型目标塞进一个任务
是否混淆 PLAN、WU、STATUS
```

### 3.6 Action 3：执行无 Skill 基线（需要单独授权）

若用户明确授权独立 Agent/隔离 Codex 验证，对每个场景使用新的只读临时工作目录运行一次，确保 prompt 不提及预期答案。记录原始输出和上述六项观察结果。

若用户未授权，明确记录：

```text
Behavioral RED baseline not run: independent agent execution was not authorized.
```

此时允许继续确定性实现，但 WU-SKILL-004 不得声称完成了行为前向验证。

### 3.7 Action 4：用官方脚本初始化 Skill

运行：

```powershell
uv run python `
  'C:\Users\lyclyc_NSP\.codex\skills\.system\skill-creator\scripts\init_skill.py' `
  managing-project-docs `
  --path 'C:\Users\lyclyc_NSP\.codex\skills' `
  --resources scripts,references,assets `
  --interface 'display_name=Project Documentation Management' `
  --interface 'short_description=Create, reorganize, and govern project documentation' `
  --interface 'default_prompt=Use $managing-project-docs to audit this project and propose a right-sized documentation structure.'
```

预期：创建 Skill 目录、`SKILL.md`、`agents/openai.yaml` 以及三个资源目录；退出码为 0。

### 3.8 Action 5：检查生成骨架

运行：

```powershell
Get-ChildItem `
  'C:\Users\lyclyc_NSP\.codex\skills\managing-project-docs' `
  -Recurse -Force |
  Select-Object FullName
```

预期：只出现 Skill Creator 生成的合法骨架，不存在 README、安装指南、变更日志或样例占位文件。

### 3.9 WU 验收

- 行为基线已执行并保留临时证据，或明确记录因未授权而未执行；
- Skill 骨架由 `init_skill.py` 创建；
- `agents/openai.yaml` 的三个 interface 字段存在；
- 未修改两个样例项目；
- 未执行 Git 操作。

---

## 4. WU-SKILL-002：核心 Skill、参考文件与模板

### 4.1 目标

让另一个 Coding Agent 能通过轻量入口选择正确模式、按需加载详细规则，并使用经过裁剪的模板创建或重组文档。

### 4.2 修改范围

- `SKILL.md`；
- `agents/openai.yaml`；
- `references/*.md`；
- `assets/templates/*.md`；
- `scripts/tests/test_skill_contract.py`。

### 4.3 Action 1：先创建失败的资源合同测试

创建 `scripts/tests/test_skill_contract.py`：

```python
from __future__ import annotations

import re
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[2]

REQUIRED_REFERENCES = {
    "document-types.md",
    "sizing-and-tailoring.md",
    "work-units.md",
    "migration-workflow.md",
    "examples.md",
    "best-practices.md",
}

REQUIRED_TEMPLATES = {
    "README.md",
    "DOCS_INDEX.md",
    "PRD.md",
    "SPEC.md",
    "ARCHITECTURE.md",
    "PLAN.md",
    "STATUS.md",
    "DESIGN.md",
    "WU.md",
    "OPTIONAL_DOCUMENT.md",
}


class SkillContractTests(unittest.TestCase):
    def test_required_resources_exist(self) -> None:
        references = {path.name for path in (SKILL_ROOT / "references").glob("*.md")}
        templates = {path.name for path in (SKILL_ROOT / "assets" / "templates").glob("*.md")}
        self.assertEqual(REQUIRED_REFERENCES, references)
        self.assertEqual(REQUIRED_TEMPLATES, templates)

    def test_skill_routes_all_three_modes(self) -> None:
        text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        for phrase in ("new project", "existing project", "new task"):
            self.assertIn(phrase, text.lower())
        self.assertIn("STATUS.md", text)
        self.assertIn("WU-<AREA>-<NNN>", text)

    def test_plan_and_work_unit_templates_do_not_store_live_status(self) -> None:
        for name in ("PLAN.md", "WU.md"):
            text = (SKILL_ROOT / "assets" / "templates" / name).read_text(encoding="utf-8")
            self.assertNotRegex(text, re.compile(r"^- \[[ xX]\]", re.MULTILINE))
            self.assertNotIn("current test count", text.lower())

    def test_templates_have_no_unresolved_placeholders(self) -> None:
        forbidden = re.compile(r"\b(?:TODO|TBD|PLACEHOLDER)\b", re.IGNORECASE)
        for path in (SKILL_ROOT / "assets" / "templates").glob("*.md"):
            self.assertIsNone(forbidden.search(path.read_text(encoding="utf-8")), path.name)


if __name__ == "__main__":
    unittest.main()
```

### 4.4 Action 2：运行合同测试并确认 RED

运行：

```powershell
python -m unittest discover `
  -s 'C:\Users\lyclyc_NSP\.codex\skills\managing-project-docs\scripts\tests' `
  -p 'test_skill_contract.py' `
  -v
```

预期：因六份 references 和十份 templates 尚不存在而失败；失败原因必须是缺少资源，不是导入或路径错误。

### 4.5 Action 3：编写 SKILL.md

frontmatter 必须只有：

```yaml
---
name: managing-project-docs
description: Use when creating documentation for a new software project, reorganizing an existing project's requirements, specifications, architecture, plans or status boards, introducing a large feature that needs Work Unit decomposition, or resolving duplicated and conflicting project documentation.
---
```

正文必须使用命令式表达，并包含：

```text
Core principle
Required initial inspection
Mode selection: new project / existing project / new task
Approval gate before writes
Small-task versus large-goal decision
Project sizing and optional-document routing
PLAN/WU/STATUS ownership
Current implementation versus target contract
Reference loading table
Template usage rules
Audit script invocation
Hard stops and final handoff
```

资源路由必须明确：

| 场景 | 必读资源 |
|---|---|
| 创建或判断文档职责 | `references/document-types.md` |
| 选择文档套餐 | `references/sizing-and-tailoring.md` |
| 拆分大型目标 | `references/work-units.md` |
| 重组已有项目 | `references/migration-workflow.md` |
| 需要实例对照 | `references/examples.md` |
| 解释外部方法来源 | `references/best-practices.md` |

`SKILL.md` 不复制完整模板和所有专题章节，目标控制在 500 行以内。

### 4.6 Action 4：编写六份 references

每份 reference 超过 100 行时在顶部增加目录。内容边界：

```text
document-types.md
  核心七文档的必需内容、不应包含内容、读者、事实源边界
  IA/Domain/Data/API/Agent/UI/Security/Deployment/Test/ADR/Runbook 条件
  图表选择规则和常见混写反例

sizing-and-tailoring.md
  规模判断维度
  小/中/大型默认套餐
  条件增量矩阵
  审计输出格式
  不以文档数量衡量成熟度

work-units.md
  大型目标、设计、WU 的关系
  上下文大小判定
  必拆信号
  WU-<AREA>-<NNN> 编号
  WU 合同章节
  PLAN/WU/STATUS 边界
  小任务升级规则

migration-workflow.md
  Git/指令/代码/测试/文档审计顺序
  当前实现/目标/历史/临时/冲突分类
  迁移矩阵格式
  分批迁移与验证后清理
  冲突决策与回滚边界

examples.md
  OrchestraAgent 的职责分层、稳定 ID、六类图和唯一 STATUS
  GRS003 的主入口、正式专题基线、taskbook、证据索引和领域模型
  可复用模式与不可复制的业务专有内容

best-practices.md
  arc42 裁剪原则
  C4 抽象层级与图表选择
  Diátaxis 目的分离
  ADR 决策记录边界
  官方链接和适用/不适用说明
```

### 4.7 Action 5：编写十份模板

模板使用描述性注释指导裁剪，但不得包含 `TODO`、`TBD` 或伪造事实。最小章节合同：

```text
README.md: 定位 / 快速开始 / 文档入口 / 最小验证
DOCS_INDEX.md: 按目标阅读 / 权威归属 / 稳定 ID / 更新矩阵
PRD.md: 职责 / 定位 / 目标 / 非目标 / 用户场景 / 流程 / 能力 / 核心对象 / 规则 / 成功指标
SPEC.md: 职责 / 功能索引 / 每项八段合同 / 跨功能状态 / 验收
ARCHITECTURE.md: 职责 / 上下文 / 组件 / 数据流 / 部署 / 技术选型 / 质量属性 / 安全 / 测试边界
PLAN.md: 职责 / 完成定义 / Phase / 依赖 / Milestone / WU 规则 / WU 索引 / 风险
STATUS.md: 当前结论 / Milestone 看板 / 当前 WU / WU 看板 / 证据 / 阻塞 / 下一步 / 维护规则
DESIGN.md: 背景 / 目标 / 非目标 / 方案比较 / 选择 / 组件与数据流 / 错误 / 测试 / 风险 / 批准
WU.md: 合同 / 背景 / 单一目标 / 依赖 / 事实源 / 范围 / 非范围 / 兼容 / 任务 / 验证 / 验收 / 回滚 / 交接 / STATUS 链接
OPTIONAL_DOCUMENT.md: 职责 / 创建条件 / 读者 / 权威范围 / 内容 / 相关文档 / 验证
```

模板必须提示执行者删除不适用章节，而不是交付空章节。

### 4.8 Action 6：校准 agents/openai.yaml

内容只保留：

```yaml
interface:
  display_name: "Project Documentation Management"
  short_description: "Create, reorganize, and govern project documentation"
  default_prompt: "Use $managing-project-docs to audit this project and propose a right-sized documentation structure."
```

不添加图标、品牌色、MCP 依赖或禁用隐式调用设置。

### 4.9 Action 7：运行合同测试并确认 GREEN

运行 Action 2 的同一命令。

预期：4 tests passed，退出码 0。

### 4.10 WU 验收

- `SKILL.md` 入口精简且能路由三种模式；
- references 与 templates 数量、文件名和职责符合设计；
- 模板无动态状态、完成勾选和未解析占位；
- `agents/openai.yaml` 与 SKILL.md 触发语义一致；
- 合同测试通过。

---

## 5. WU-SKILL-003：确定性文档审计 CLI

### 5.1 目标

提供一个无第三方运行时依赖、不会修改项目的只读 CLI，发现结构、链接、事实源边界和 WU 合同中的确定性问题。

### 5.2 公共接口

`scripts/audit_docs.py` 暴露以下精确接口：

| 对象 | 字段或签名 | 行为 |
|---|---|---|
| `AuditFinding` | frozen dataclass：`code: str`、`severity: Literal["error", "warning"]`、`path: str`、`message: str` | 表示一条稳定、可序列化的问题 |
| `AuditReport` | frozen dataclass：`root: Path`、`findings: tuple[AuditFinding, ...]` | 保存一次完整审计结果 |
| `AuditReport.error_count` | 只读 property，返回 `sum(f.severity == "error" for f in findings)` | CLI 退出码依据 |
| `audit_project` | `audit_project(root: Path) -> AuditReport` | 校验根目录后执行全部只读检查，findings 按 path、code、message 稳定排序 |
| `main` | `main(argv: Sequence[str] | None = None) -> int` | 解析参数，输出文本或 JSON，并返回 0、1、2 |

CLI：

```text
python audit_docs.py <project-root> [--json]
```

退出码：0 表示无 error；1 表示发现 error；2 表示参数或根目录无效。

### 5.3 Action 1：先写失败的审计测试

创建 `scripts/tests/test_audit_docs.py`，使用 `tempfile.TemporaryDirectory` 和 `unittest`。文件顶部加入：

```python
from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

from audit_docs import audit_project, main
```

建立 `write_minimal_project(root: Path) -> None` helper，创建下方七个核心文件，并写入满足所有必要章节的最短正文。逐条测试合同如下，不得合并用例：

| 测试名 | fixture 变化 | 精确断言 |
|---|---|---|
| `test_minimal_valid_project_has_no_errors` | 无 | `audit_project(root).error_count == 0` |
| `test_missing_core_document_is_error` | 删除 `docs/product/SPEC.md` | findings 包含 code `DOC001` 且 path 为 `docs/product/SPEC.md` |
| `test_broken_relative_link_is_error` | PRD 加入 `[missing](missing.md)` | findings 包含 `DOC002` 和目标 `missing.md` |
| `test_external_and_anchor_links_are_ignored` | PRD 加入 HTTPS、mailto 和 `#section` | findings 不包含 `DOC002` |
| `test_links_inside_fenced_code_are_ignored` | fenced Markdown 中写 `[fake](missing.md)` | findings 不包含 `DOC002` |
| `test_plan_checkbox_is_error` | PLAN 加入 `- [ ] implementation` | findings 包含 `PLAN001` |
| `test_work_unit_invalid_id_is_error` | 创建 `docs/planning/work-units/task-login.md` | findings 包含 `WU001` |
| `test_work_unit_missing_contract_section_is_error` | 创建合法文件名但缺少“非范围”章节 | findings 包含 `WU002`，message 指出 `非范围` |
| `test_status_missing_evidence_section_is_error` | STATUS 删除“验证证据”章节 | findings 包含 `STATUS001` |
| `test_root_and_docs_duplicate_is_warning` | 同时创建根 `PRD.md` | findings 包含 severity `warning` 的 `DOC004` |
| `test_cli_json_output_and_exit_code` | 删除 SPEC，使用 `contextlib.redirect_stdout` 调用 `main([str(root), "--json"])` | 返回 1；`json.loads(stdout)` 成功；对象中 `error_count == 1` |

测试 fixture 的最小合法项目必须创建：

```text
README.md
docs/README.md
docs/product/PRD.md
docs/product/SPEC.md
docs/architecture/ARCHITECTURE.md
docs/planning/PLAN.md
docs/planning/STATUS.md
```

### 5.4 Action 2：运行测试并确认 RED

运行：

```powershell
python -m unittest discover `
  -s 'C:\Users\lyclyc_NSP\.codex\skills\managing-project-docs\scripts\tests' `
  -p 'test_audit_docs.py' `
  -v
```

预期：因 `audit_docs` 模块或公共对象不存在而失败。

### 5.5 Action 3：实现最小审计模型和 CLI

使用标准库：`argparse`、`dataclasses`、`json`、`pathlib`、`re`、`typing`。不得添加依赖。

检查码固定为：

```text
DOC001 missing-core-document        error
DOC002 broken-relative-link         error
DOC003 unresolved-placeholder       warning
DOC004 duplicate-formal-document    warning
PLAN001 live-checkbox               error
PLAN002 missing-plan-section        error
STATUS001 missing-status-section    error
WU001 invalid-work-unit-id          error
WU002 missing-work-unit-section     error
WU003 live-status-in-work-unit      error
```

Markdown 链接解析必须忽略：

- `http://`、`https://`、`mailto:`；
- 纯 `#anchor`；
- fenced code block 内文本；
- 图片链接可使用同一相对路径存在性检查。

重复正式文档只检查以下根目录与 docs 对照，不猜测语义相似度：

```text
PRD.md ↔ docs/product/PRD.md
SPEC.md ↔ docs/product/SPEC.md
ARCHITECTURE.md ↔ docs/architecture/ARCHITECTURE.md
PLAN.md ↔ docs/planning/PLAN.md
STATUS.md ↔ docs/planning/STATUS.md
```

### 5.6 Action 4：运行测试并确认 GREEN

运行 Action 2 的同一命令。

预期：基础 11 个合同测试通过；若真实项目审计暴露通用误报，必须先增加回归测试再修正实现，并以最终新鲜测试数量为准。

### 5.7 Action 5：运行 CLI 手工合同

运行：

```powershell
python `
  'C:\Users\lyclyc_NSP\.codex\skills\managing-project-docs\scripts\audit_docs.py' `
  --help
```

预期：显示 `<project-root>` 和 `--json`，退出码 0。

再对 OrchestraAgent 运行只读审计：

```powershell
python `
  'C:\Users\lyclyc_NSP\.codex\skills\managing-project-docs\scripts\audit_docs.py' `
  'D:\000MyWorkSpace\001ActiveProjects\OrchestraAgent' `
  --json
```

预期：输出合法 JSON。发现项目特有差异时如实报告，不为了让样例项目“全绿”而放宽通用合同。

### 5.8 WU 验收

- 脚本只读且只依赖 Python 标准库；
- 公共对象、检查码和退出码固定；
- 11 个行为测试先 RED 后 GREEN；
- `--help` 和 JSON 输出可用；
- 未把内容正确性伪装成自动验证能力。

---

## 6. WU-SKILL-004：综合验证与交付

### 6.1 目标

证明 Skill 目录合法、静态合同和审计行为通过，并在获得授权时验证它能改变独立 Agent 的文档治理行为。

### 6.2 Action 1：运行全部本地测试

```powershell
python -m unittest discover `
  -s 'C:\Users\lyclyc_NSP\.codex\skills\managing-project-docs\scripts\tests' `
  -p 'test_*.py' `
  -v
```

预期：资源合同与审计行为测试全部通过，退出码 0；不得预先把计划中的初始测试数量当成最终证据。

### 6.3 Action 2：运行官方 Skill 校验

系统 Python 当前缺少 PyYAML，因此使用 OrchestraAgent 的 uv 环境：

```powershell
$env:PYTHONUTF8 = '1'
uv run python `
  'C:\Users\lyclyc_NSP\.codex\skills\.system\skill-creator\scripts\quick_validate.py' `
  'C:\Users\lyclyc_NSP\.codex\skills\managing-project-docs'
```

预期：输出 `Skill is valid!`，退出码 0。Windows 上显式使用 UTF-8，避免官方脚本按默认 GBK 读取中文；不全局安装 PyYAML。

### 6.4 Action 3：检查资源和占位

```powershell
$skill = 'C:\Users\lyclyc_NSP\.codex\skills\managing-project-docs'
$files = @(Get-Item "$skill\SKILL.md")
$files += Get-ChildItem "$skill\references","$skill\assets\templates" -Recurse -File
$files | Select-String -Pattern '\bTODO\b|\bTBD\b|PLACEHOLDER' -CaseSensitive:$false
```

预期：无输出。

检查 SKILL.md 长度：

```powershell
(Get-Content "$skill\SKILL.md").Count
```

预期：不超过 500 行。

### 6.5 Action 4：执行 GREEN 前向测试（需要单独授权）

若用户明确授权独立 Agent/隔离 Codex 验证，使用 WU-SKILL-001 的同三个 prompt，每个场景使用全新的临时目录，并明确要求使用 `$managing-project-docs`。不得把预期答案、设计文档或 baseline 观察结论传给执行者。

通过标准：

```text
SCENARIO-NEW:
  先判断规模；核心文档不过度扩张；条件型文档有创建依据。

SCENARIO-MIGRATION:
  先审计和提出迁移矩阵；不直接删除；区分当前实现、目标和历史。

SCENARIO-LARGE-FEATURE:
  把 OAuth、数据库/权限、前端体验拆成多个可理解 WU；PLAN/WU/STATUS 职责正确。
```

若未获授权，最终交付必须写明“未执行独立 Agent 前向测试”，不得声称 Skill 行为已在真实触发环境验证。

### 6.6 Action 5：验证可发现性元数据

读取 `SKILL.md` frontmatter 和 `agents/openai.yaml`，确认：

- name 等于目录名；
- description 只描述触发条件，不总结详细执行步骤；
- default_prompt 明确包含 `$managing-project-docs`；
- 无多余依赖和产品特有业务词。

### 6.7 Action 6：最终交付

最终回复必须包含：

1. Skill 安装路径；
2. 三种模式和 WU 规则摘要；
3. 创建的文件分组；
4. 单元测试、quick_validate、CLI 和前向测试结果；
5. 未验证或受权限限制的部分；
6. 没有执行 commit/push 的说明；
7. 一个可直接尝试的调用示例：

```text
Use $managing-project-docs to audit this project and propose a right-sized documentation structure.
```

### 6.8 WU 验收

- 全部确定性测试通过，并报告执行时的新鲜数量；
- 官方 quick_validate 通过；
- 无未解析占位，SKILL.md 不超过 500 行；
- 前向测试通过，或因未授权明确列为限制；
- Skill 已位于个人自动发现目录；
- 未执行未经授权的 Git、删除、安装或部署操作。

---

## 7. 整体风险与控制

### 7.1 Skill 过长

控制：SKILL.md 只保留流程、硬约束和资源路由；详细规则拆入一层 references；不允许 references 相互深层跳转。

### 7.2 模板导致过度文档化

控制：规模套餐只是默认值，条件矩阵决定增删；模板必须删除不适用章节；小型项目测试必须证明不会自动生成所有专题。

### 7.3 审计脚本误判内容正确

控制：脚本只输出结构性 finding；内容、架构和冲突决策保留给 Agent 与用户；报告中区分 error 和 warning。

### 7.4 个人 Skill 影响现有项目

控制：测试使用临时目录；对真实项目只读审计；任何创建、迁移、删除和 Git 操作仍经过用户确认。

### 7.5 缺少独立 Agent 验证

控制：由于当前指令不允许未经明确请求派发子 Agent，前向测试作为显式授权门。未授权时完成静态和确定性验证，但不得把它描述为完整行为验证。

## 8. 整体完成定义

只有同时满足以下条件，才可声明 Skill 实现完成：

1. WU-SKILL-001 至 WU-SKILL-004 的产物和验证均可追溯；
2. Skill 目录通过官方校验；
3. references、templates 和脚本职责与批准设计一致；
4. 所有确定性测试通过；
5. 对前向测试是否执行及其结果没有模糊表述；
6. Skill 可被个人 Codex 自动发现；
7. 未修改样例项目业务内容；
8. 未执行未经授权的 commit、push、删除、依赖安装或部署。
