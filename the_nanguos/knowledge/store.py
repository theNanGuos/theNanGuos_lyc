from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path

import yaml
from pydantic import TypeAdapter, ValidationError

from .models import (
    KnowledgeCatalog,
    KnowledgeDocument,
    KnowledgeFrontmatter,
    KnowledgeType,
    KnowledgeWarning,
    TrackKnowledge,
)


FRONTMATTER_ADAPTER = TypeAdapter(KnowledgeFrontmatter)
DIRECTORY_TYPES = {
    "styles": KnowledgeType.STYLE,
    "instruments": KnowledgeType.INSTRUMENT,
    "tracks": KnowledgeType.TRACK,
}
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


class DirectoryTypeMismatch(ValueError):
    pass


class KnowledgeStore:
    def __init__(self, root: Path | str = "knowledge") -> None:
        self.root = Path(root)
        self.index_path = self.root / "_index" / "catalog.json"

    def load_catalog(self) -> KnowledgeCatalog:
        if not self.root.is_dir() or self.root.is_symlink():
            warning = (
                KnowledgeWarning(code="unsafe_path", message="knowledge root must not be a symbolic link")
                if self.root.is_symlink()
                else KnowledgeWarning(code="knowledge_root_missing", message="knowledge directory is unavailable")
            )
            return KnowledgeCatalog(
                indexed_at=datetime.now(UTC),
                fingerprint=hashlib.sha256(b"missing-knowledge-root").hexdigest(),
                warnings=[warning],
            )

        files, scan_warnings = self._source_files()
        fingerprint = self._fingerprint(files, scan_warnings)
        cached = self._read_cache(fingerprint)
        if cached is not None:
            return cached

        documents: list[KnowledgeDocument] = []
        warnings: list[KnowledgeWarning] = list(scan_warnings)
        ids: set[str] = set()
        for path, expected_type in files:
            relative = path.relative_to(self.root).as_posix()
            try:
                document = self._parse_document(path, expected_type)
            except DirectoryTypeMismatch as exc:
                warnings.append(KnowledgeWarning(code="directory_type_mismatch", message=str(exc), source_path=relative))
                continue
            except (OSError, UnicodeError, ValueError, TypeError, yaml.YAMLError, ValidationError) as exc:
                warnings.append(KnowledgeWarning(code="invalid_document", message=type(exc).__name__, source_path=relative))
                continue
            if document.frontmatter.id in ids:
                warnings.append(KnowledgeWarning(code="duplicate_id", message="knowledge id is duplicated", source_path=relative))
                continue
            ids.add(document.frontmatter.id)
            documents.append(document)

        remaining = {document.frontmatter.id: document for document in documents}
        while True:
            invalid: list[tuple[KnowledgeDocument, list[str]]] = []
            for document in remaining.values():
                missing = sorted(set(self._references(document)) - remaining.keys())
                if missing:
                    invalid.append((document, missing))
            if not invalid:
                break
            for document, missing in invalid:
                remaining.pop(document.frontmatter.id, None)
                warnings.append(
                    KnowledgeWarning(
                        code="missing_reference",
                        message=f"missing references: {', '.join(missing)}",
                        source_path=document.source_path,
                    )
                )
        validated = list(remaining.values())

        catalog = KnowledgeCatalog(
            indexed_at=datetime.now(UTC),
            fingerprint=fingerprint,
            documents=validated,
            warnings=warnings,
        )
        try:
            self._write_cache(catalog)
        except OSError:
            catalog.warnings.append(KnowledgeWarning(code="cache_write_failed", message="knowledge index could not be updated"))
        return catalog

    def _source_files(self) -> tuple[list[tuple[Path, KnowledgeType]], list[KnowledgeWarning]]:
        files: list[tuple[Path, KnowledgeType]] = []
        warnings: list[KnowledgeWarning] = []
        resolved_root = self.root.resolve()
        for directory, kind in DIRECTORY_TYPES.items():
            folder = self.root / directory
            if folder.is_symlink():
                warnings.append(
                    KnowledgeWarning(
                        code="unsafe_path",
                        message="symbolic-link knowledge directories are ignored",
                        source_path=directory,
                    )
                )
                continue
            if not folder.is_dir():
                continue
            for path in folder.glob("*.md"):
                relative = path.relative_to(self.root).as_posix()
                if path.is_symlink():
                    warnings.append(KnowledgeWarning(code="unsafe_path", message="symbolic-link knowledge files are ignored", source_path=relative))
                    continue
                try:
                    path.resolve().relative_to(resolved_root)
                except (OSError, ValueError):
                    warnings.append(KnowledgeWarning(code="unsafe_path", message="knowledge path escapes its root", source_path=relative))
                    continue
                if path.is_file():
                    files.append((path, kind))
        ordered = sorted(files, key=lambda item: item[0].relative_to(self.root).as_posix())
        return ordered, warnings

    def _fingerprint(self, files: list[tuple[Path, KnowledgeType]], warnings: list[KnowledgeWarning]) -> str:
        digest = hashlib.sha256()
        for path, _ in files:
            stat = path.stat()
            digest.update(path.relative_to(self.root).as_posix().encode("utf-8"))
            digest.update(f"\0{stat.st_size}\0{stat.st_mtime_ns}\n".encode())
        for warning in warnings:
            digest.update(f"{warning.code}\0{warning.source_path or ''}\n".encode("utf-8"))
        return digest.hexdigest()

    def _read_cache(self, fingerprint: str) -> KnowledgeCatalog | None:
        try:
            payload = json.loads(self.index_path.read_text(encoding="utf-8"))
            catalog = KnowledgeCatalog.model_validate(payload)
        except (OSError, ValueError, TypeError, ValidationError):
            return None
        return catalog if catalog.fingerprint == fingerprint else None

    def _write_cache(self, catalog: KnowledgeCatalog) -> None:
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.index_path.with_suffix(".json.tmp")
        try:
            temporary.write_text(catalog.model_dump_json(indent=2) + "\n", encoding="utf-8")
            os.replace(temporary, self.index_path)
        except OSError:
            temporary.unlink(missing_ok=True)
            raise

    def _parse_document(self, path: Path, expected_type: KnowledgeType) -> KnowledgeDocument:
        text = path.read_text(encoding="utf-8-sig")
        lines = text.splitlines()
        if not lines or lines[0].strip() != "---":
            raise ValueError("missing YAML frontmatter")
        try:
            end = next(index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---")
        except StopIteration as exc:
            raise ValueError("unterminated YAML frontmatter") from exc
        metadata = yaml.safe_load("\n".join(lines[1:end]))
        if not isinstance(metadata, dict):
            raise ValueError("frontmatter must be a mapping")
        frontmatter = FRONTMATTER_ADAPTER.validate_python(metadata)
        if frontmatter.type != expected_type:
            raise DirectoryTypeMismatch(f"expected {expected_type}, got {frontmatter.type}")
        body = "\n".join(lines[end + 1 :]).strip()
        return KnowledgeDocument(
            frontmatter=frontmatter,
            body=body,
            sections=self._split_sections(body),
            source_path=path.relative_to(self.root).as_posix(),
        )

    @staticmethod
    def _split_sections(body: str) -> dict[str, str]:
        sections: dict[str, str] = {}
        current: str | None = None
        content: list[str] = []
        for line in body.splitlines():
            match = HEADING_PATTERN.match(line)
            if match:
                if current is not None:
                    sections[current] = "\n".join(content).strip()
                current = match.group(2).strip()
                content = []
            elif current is not None:
                content.append(line)
        if current is not None:
            sections[current] = "\n".join(content).strip()
        return sections

    @staticmethod
    def _references(document: KnowledgeDocument) -> list[str]:
        metadata = document.frontmatter
        references = [*metadata.related_styles, *metadata.related_instruments, *metadata.reference_tracks]
        if isinstance(metadata, TrackKnowledge):
            references.extend(metadata.style_refs)
        return references
