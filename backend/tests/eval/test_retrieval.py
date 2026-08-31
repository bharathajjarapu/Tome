"""Retrieval quality on a real corpus, scored the way retrieval benchmarks score it.

Hit rate, MRR and NDCG over a question set with a known correct source document -- the same
metrics BEIR-style benchmarks report, on a corpus small enough to run in a couple of minutes.

Left out of the default run because it downloads and embeds three papers:

    uv run pytest -m eval -s
"""

import uuid
from collections import defaultdict

import pytest

from pka.ingestion.nodes import build
from pka.ingestion.parse import parse
from pka.rag import store
from pka.rag.rerank import Reranker
from tests.eval.corpus import QUESTIONS, fetch
from tests.eval.scoring import Reranked, report, score

pytestmark = pytest.mark.eval

TEAM, PROJECT = uuid.uuid4(), uuid.uuid4()


@pytest.fixture
def corpus() -> dict[str, list[str]]:
    """Index the papers and return each one's node ids, which are the answers to grade against."""
    ids = defaultdict(list)
    for name, data in fetch().items():
        nodes = build(
            parse(data, name),
            team_id=TEAM,
            project_id=PROJECT,
            document_id=uuid.uuid4(),
            document_name=name,
        )
        store.add(nodes)
        ids[name] = [node.node_id for node in nodes]
    return ids


def test_retrieval_finds_the_right_paper(corpus: dict[str, list[str]]) -> None:
    """The reranked passages are what the model sees, so they are what has to be right."""
    graded = [(question, corpus[source]) for question, source in QUESTIONS]
    retriever = store.retriever(TEAM, PROJECT)
    before = score(retriever, graded)
    after = score(Reranked(retriever, Reranker()), graded)

    report(
        f"{len(QUESTIONS)} questions over {len(corpus)} papers",
        {"retrieved": before, "reranked": after},
    )

    # Measured 1.000 / 1.000 with a little slack. NDCG is printed but not asserted: the two
    # rows retrieve different numbers of nodes, so their NDCG is not comparable.
    assert after["hit_rate"] >= 0.95
    assert after["mrr"] >= 0.90
