from pathlib import Path

from the_nanguos.knowledge import KnowledgeStore, KnowledgeType


def test_bundled_manual_knowledge_examples_validate_as_a_connected_catalog() -> None:
    root = Path(__file__).resolve().parents[1] / "knowledge"

    catalog = KnowledgeStore(root).load_catalog()

    assert {document.frontmatter.type for document in catalog.documents} == set(KnowledgeType)
    assert len(catalog.documents) == 3
    assert catalog.warnings == []
