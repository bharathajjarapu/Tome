"""The vector store seam: hybrid retrieval, scoped to one project, and forgetting a document."""

import uuid

import pytest
from llama_index.core import Document
from llama_index.core.node_parser import MarkdownNodeParser

from pka.rag import store

TEAM_A, PROJECT_A = uuid.uuid4(), uuid.uuid4()
TEAM_B, PROJECT_B = uuid.uuid4(), uuid.uuid4()

DOC_A = uuid.uuid4()
DOC_B = uuid.uuid4()


def doc(text: str, team: uuid.UUID, project: uuid.UUID, document: uuid.UUID) -> Document:
    """A document identified the way LlamaIndex identifies one, so `forget` can find its nodes."""
    return Document(
        text=text,
        id_=str(document),
        metadata={
            "team_id": str(team),
            "project_id": str(project),
            "document_name": "notes.md",
        },
    )


@pytest.fixture(autouse=True)
def seeded() -> None:
    store.add(
        MarkdownNodeParser().get_nodes_from_documents(
            [
                doc(
                    "# Retention\n\nArchived logs are kept for ninety days.",
                    TEAM_A, PROJECT_A, DOC_A,
                ),
                doc("# Coffee\n\nThe espresso machine needs descaling.", TEAM_B, PROJECT_B, DOC_B),
            ]
        )
    )


def test_a_question_finds_its_own_project() -> None:
    found = store.retriever(TEAM_A, PROJECT_A).retrieve("how long are logs kept")
    assert found
    assert "ninety days" in found[0].node.text


def test_another_teams_content_never_comes_back() -> None:
    scoped = store.retriever(TEAM_A, PROJECT_A)
    for query in ("descaling the espresso machine", "espresso", "how long are logs kept"):
        assert all("espresso" not in hit.node.text for hit in scoped.retrieve(query))


def test_hits_carry_citation_metadata() -> None:
    hit = store.retriever(TEAM_A, PROJECT_A).retrieve("retention")[0]
    assert hit.node.metadata["document_name"] == "notes.md"
    assert hit.node.metadata["header_path"]
    assert hit.node.ref_doc_id == str(DOC_A)
    assert hit.score is not None


def test_the_filters_cannot_be_left_out() -> None:
    with pytest.raises(TypeError):
        store.retriever()  # type: ignore[call-arg]


def test_forget_removes_only_that_document() -> None:
    store.forget(DOC_B)
    assert store.count(DOC_B) == 0
    assert store.count(DOC_A) > 0
