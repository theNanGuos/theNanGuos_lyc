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
    DOCS / "planning" / "designs" / "2026-07-15-post-mvp-ux-library-design.md",
    DOCS / "planning" / "work-units" / "WU-API-002.md",
    DOCS / "planning" / "work-units" / "WU-DOC-001.md",
    DOCS / "planning" / "work-units" / "WU-QA-002.md",
    DOCS / "planning" / "work-units" / "WU-SUNO-002.md",
    DOCS / "planning" / "work-units" / "WU-WEB-002.md",
    DOCS / "planning" / "work-units" / "WU-WEB-003.md",
]

LEGACY_ROOT_DOCS = [
    "PRD.md",
    "SPEC.md",
    "ARCHITECTURE.md",
    "INFORMATION_ARCHITECTURE.md",
    "PLAN.md",
    "STATUS.md",
    "WEB_UI_DESIGN.md",
]

MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def markdown_links(text: str) -> list[str]:
    visible_lines: list[str] = []
    in_fence = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence:
            visible_lines.append(line)
    return MARKDOWN_LINK.findall("\n".join(visible_lines))


def test_required_documentation_exists() -> None:
    missing = [path.relative_to(ROOT).as_posix() for path in REQUIRED_DOCS if not path.is_file()]
    assert missing == []


def test_legacy_root_document_copies_are_removed() -> None:
    remaining = [name for name in LEGACY_ROOT_DOCS if (ROOT / name).exists()]
    assert remaining == []


def test_plan_uses_phases_and_work_units_without_progress_checkboxes() -> None:
    plan = read("docs/planning/PLAN.md")
    assert all(f"P{number}" in plan for number in range(1, 11))
    assert "M6" in plan
    assert all(wu in plan for wu in ["WU-WEB-002", "WU-SUNO-002", "WU-WEB-003", "WU-API-002", "WU-QA-002"])
    assert "Work Unit" in plan
    assert "阶段 19" not in plan
    assert not re.search(r"^- \[[ xX]\]", plan, flags=re.MULTILINE)


def test_work_unit_delegates_status_to_status_board() -> None:
    work_units = sorted((DOCS / "planning" / "work-units").glob("WU-*.md"))
    for path in work_units:
        work_unit = path.read_text(encoding="utf-8")
        assert "**实际状态：** 见 [`STATUS.md`](../STATUS.md)。" in work_unit
        assert not re.search(r"^- \[[ xX]\]", work_unit, flags=re.MULTILINE)


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


def test_markdown_links_ignore_fenced_code() -> None:
    markdown = """[real](real.md)
```markdown
[example](missing.md)
```
"""
    assert list(markdown_links(markdown)) == ["real.md"]


def test_relative_markdown_links_resolve() -> None:
    broken: list[str] = []
    for path in REQUIRED_DOCS:
        text = path.read_text(encoding="utf-8")
        for target in markdown_links(text):
            if target.startswith(("http://", "https://", "#")):
                continue
            file_target = target.split("#", 1)[0]
            if file_target and not (path.parent / file_target).resolve().exists():
                broken.append(f"{path.relative_to(ROOT).as_posix()} -> {target}")
    assert broken == []
