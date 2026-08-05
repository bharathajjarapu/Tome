"""Retrieval quality on a real corpus, scored the way retrieval benchmarks score it.

Hit rate, MRR and NDCG over a question set with a known correct source document -- the same
metrics BEIR-style benchmarks report, on a corpus small enough to run in a couple of minutes.

Left out of the default run because it downloads and embeds three papers:

    uv run pytest -m eval -s
"""

import uuid
from collections import defaultdict

import pytest
from llama_index.core.evaluation.retrieval.metrics import resolve_metrics
from llama_index.core.retrievers import BaseRetriever
from llama_index.core.schema import NodeWithScore, QueryBundle

from pka.ingestion.nodes import build
from pka.ingestion.parse import parse
from pka.rag import store
from pka.rag.rerank import Reranker
from tests.eval.corpus import QUESTIONS, fetch

pytestmark = pytest.mark.eval

TEAM, PROJECT = uuid.uuid4(), uuid.uuid4()
METRICS = ["hit_rate", "mrr", "ndcg"]


class Reranked(BaseRetriever):
    """What actually reaches the model: the retriever's candidates, cut down by the reranker."""

    def __init__(self, inner: BaseRetriever, reranker: Reranker) -> None:
        self._inner = inner
        self._reranker = reranker
        super().__init__()

    def _retrieve(self, query: QueryBundle) -> list[NodeWithScore]:
        return self._reranker.postprocess_nodes(self._inner.retrieve(query), query)


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


def score(retriever: BaseRetriever, corpus: dict[str, list[str]]) -> dict[str, float]:
    """Mean of each metric over the question set, scored on the ids that came back."""
    metrics = [metric() for metric in resolve_metrics(METRICS)]
    totals: dict[str, float] = defaultdict(float)
    for question, source in QUESTIONS:
        found = [node.node_id for node in retriever.retrieve(question)]
        for metric in metrics:
            result = metric.compute(question, expected_ids=corpus[source], retrieved_ids=found)
            totals[metric.metric_name] += (result.score or 0.0) / len(QUESTIONS)
    return dict(totals)


def test_retrieval_finds_the_right_paper(corpus: dict[str, list[str]]) -> None:
    """The reranked passages are what the model sees, so they are what has to be right."""
    retriever = store.retriever(TEAM, PROJECT)
    before = score(retriever, corpus)
    after = score(Reranked(retriever, Reranker()), corpus)

    print(f"\n{len(QUESTIONS)} questions over {len(corpus)} papers")
    print(f"{'':10} {'hit_rate':>9} {'mrr':>9} {'ndcg':>9}")
    for label, results in (("retrieved", before), ("reranked", after)):
        print(f"{label:10} " + " ".join(f"{results[m]:9.3f}" for m in METRICS))

    # Measured 1.000 / 1.000 with a little slack. NDCG is printed but not asserted: the two
    # rows retrieve different numbers of nodes, so their NDCG is not comparable.
    assert after["hit_rate"] >= 0.95
    assert after["mrr"] >= 0.90
