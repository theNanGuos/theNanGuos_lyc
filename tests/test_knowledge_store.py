from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from the_nanguos.knowledge import KnowledgeType
from the_nanguos.knowledge.store import KnowledgeStore


def write_entry(
    root: Path,
    folder: str,
    slug: str,
    *,
    kind: str,
    entry_id: str | None = None,
    references: str = "",
    extra: str = "",
    bom: bool = False,
) -> Path:
    path = root / folder / f"{slug}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    track = "artist: Example Artist\nyear: 1982\nstyle_refs:\n  - style.city_pop\n" if kind == "track" else ""
    content = f"""---
id: {entry_id or f'{kind}.{slug}'}
type: {kind}
name: {slug.replace('_', ' ').title()}
aliases:
  - {slug}
tags:
  - warm
sources:
  - https://example.com/{slug}
updated_at: 2026-07-14
{references}{track}{extra}---
# 定义

{slug} 的定义内容。

## 制作边界

保持动态与空间。
"""
    path.write_text(content, encoding="utf-8-sig" if bom else "utf-8")
    return path


def complete_library(root: Path) -> None:
    write_entry(root, "styles", "city_pop", kind="style")
    write_entry(
        root,
        "instruments",
        "electric_piano",
        kind="instrument",
        references="related_styles:\n  - style.city_pop\n",
        bom=True,
    )
    write_entry(root, "tracks", "plastic_love", kind="track")


def test_store_parses_three_types_sections_and_reuses_unchanged_cache(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "knowledge"
    complete_library(root)
    store = KnowledgeStore(root)

    first = store.load_catalog()
    monkeypatch.setattr(store, "_parse_document", lambda *args: (_ for _ in ()).throw(AssertionError("cache miss")))
    second = store.load_catalog()

    assert {doc.frontmatter.type for doc in first.documents} == set(KnowledgeType)
    assert first.documents[0].sections
    assert first.fingerprint == second.fingerprint
    assert first.indexed_at == second.indexed_at
    assert (root / "_index" / "catalog.json").is_file()


def test_store_excludes_bad_entries_but_keeps_valid_documents(tmp_path: Path) -> None:
    root = tmp_path / "knowledge"
    write_entry(root, "styles", "valid", kind="style")
    write_entry(root, "styles", "duplicate", kind="style", entry_id="style.valid")
    write_entry(root, "instruments", "wrong_folder", kind="style")
    write_entry(
        root,
        "instruments",
        "missing_reference",
        kind="instrument",
        references="related_styles:\n  - style.does_not_exist\n",
    )
    broken = root / "tracks" / "broken.md"
    broken.parent.mkdir(parents=True)
    broken.write_text("not frontmatter", encoding="utf-8")

    catalog = KnowledgeStore(root).load_catalog()

    assert [doc.frontmatter.id for doc in catalog.documents] == ["style.valid"]
    assert {warning.code for warning in catalog.warnings} >= {
        "duplicate_id",
        "directory_type_mismatch",
        "missing_reference",
        "invalid_document",
    }


def test_store_refreshes_catalog_when_file_set_or_mtime_changes(tmp_path: Path) -> None:
    root = tmp_path / "knowledge"
    first_path = write_entry(root, "styles", "first", kind="style")
    store = KnowledgeStore(root)
    first = store.load_catalog()

    write_entry(root, "instruments", "second", kind="instrument")
    second = store.load_catalog()
    stat = first_path.stat()
    os.utime(first_path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000))
    third = store.load_catalog()

    assert first.fingerprint != second.fingerprint
    assert second.fingerprint != third.fingerprint
    assert len(second.documents) == 2


def test_store_removes_documents_that_reference_an_excluded_document(tmp_path: Path) -> None:
    root = tmp_path / "knowledge"
    write_entry(
        root,
        "styles",
        "root",
        kind="style",
        references="related_instruments:\n  - instrument.broken\n",
    )
    write_entry(
        root,
        "instruments",
        "broken",
        kind="instrument",
        references="related_styles:\n  - style.missing\n",
    )

    catalog = KnowledgeStore(root).load_catalog()

    assert catalog.documents == []
    assert [warning.code for warning in catalog.warnings].count("missing_reference") == 2


def test_store_keeps_old_cache_when_atomic_replace_fails(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "knowledge"
    write_entry(root, "styles", "first", kind="style")
    store = KnowledgeStore(root)
    store.load_catalog()
    cache_path = root / "_index" / "catalog.json"
    old_cache = cache_path.read_text(encoding="utf-8")
    write_entry(root, "instruments", "second", kind="instrument")

    monkeypatch.setattr("the_nanguos.knowledge.store.os.replace", lambda *_: (_ for _ in ()).throw(OSError("locked")))
    catalog = store.load_catalog()

    assert cache_path.read_text(encoding="utf-8") == old_cache
    assert any(warning.code == "cache_write_failed" for warning in catalog.warnings)
    assert json.loads(old_cache)["documents"]


def test_store_returns_degraded_empty_catalog_when_root_is_missing(tmp_path: Path) -> None:
    catalog = KnowledgeStore(tmp_path / "missing").load_catalog()

    assert catalog.documents == []
    assert catalog.fingerprint
    assert catalog.warnings[0].code == "knowledge_root_missing"
