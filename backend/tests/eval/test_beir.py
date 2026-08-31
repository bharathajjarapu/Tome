"""The same retrieval scored against a public benchmark rather than our own questions.

Downloads SciFact into .eval-cache and embeds a slice of it:

    uv run pytest -m eval -s -k beir
"""

import uuid

import pytest

from pka.ingestion.nodes import build
from pka.rag import store
from pka.rag.rerank import Reranker
from tests.eval.beir import load
from tests.eval.scoring import Reranked, report, score

pytestmark = pytest.mark.eval

TEAM, PROJECT = uuid.uuid4(), uuid.uuid4()


def test_retrieval_on_a_public_benchmark() -> None:
    """A neutral corpus nobody tuned against, graded on the passage rather than the document."""
    corpus, asked = load()

    nodes_by_document: dict[str, list[str]] = {}
    for document, text in corpus.items():
        nodes = build(
            text,
            team_id=TEAM,
            project_id=PROJECT,
            document_id=uuid.uuid4(),
            document_name=document,
        )
        store.add(nodes)
        nodes_by_document[document] = [node.node_id for node in nodes]

    graded = [
        (question, [node for doc in docs for node in nodes_by_document.get(doc, [])])
        for question, docs in asked
    ]
    retriever = store.retriever(TEAM, PROJECT)
    reranked = score(Reranked(retriever, Reranker()), graded)
    report(
        f"{len(graded)} SciFact queries over {len(corpus)} abstracts",
        {"retrieved": score(retriever, graded), "reranked": reranked},
    )

    # A floor, not a target: this catches a pipeline that has stopped working, and leaves the
    # actual numbers to be read and compared between runs.
    assert reranked["hit_rate"] >= 0.5
