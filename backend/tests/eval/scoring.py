"""Scoring shared by the eval suites: the metrics, and what the model actually sees."""

from collections import defaultdict
from collections.abc import Sequence

from llama_index.core.evaluation.retrieval.metrics import resolve_metrics
from llama_index.core.retrievers import BaseRetriever
from llama_index.core.schema import NodeWithScore, QueryBundle

from pka.rag.rerank import Reranker

METRICS = ["hit_rate", "mrr", "ndcg"]


class Reranked(BaseRetriever):
    """What actually reaches the model: the retriever's candidates, cut down by the reranker."""

    def __init__(self, inner: BaseRetriever, reranker: Reranker) -> None:
        self._inner = inner
        self._reranker = reranker
        super().__init__()

    def _retrieve(self, query: QueryBundle) -> list[NodeWithScore]:
        return self._reranker.postprocess_nodes(self._inner.retrieve(query), query)


def score(
    retriever: BaseRetriever, questions: Sequence[tuple[str, Sequence[str]]]
) -> dict[str, float]:
    """Mean of each metric over the question set, scored on the ids that came back."""
    metrics = [metric() for metric in resolve_metrics(METRICS)]
    totals: dict[str, float] = defaultdict(float)
    for question, expected in questions:
        found = [node.node_id for node in retriever.retrieve(question)]
        for metric in metrics:
            result = metric.compute(question, expected_ids=list(expected), retrieved_ids=found)
            totals[metric.metric_name] += (result.score or 0.0) / len(questions)
    return dict(totals)


def report(label: str, rows: dict[str, dict[str, float]]) -> None:
    print(f"\n{label}")
    print(f"{'':10} " + " ".join(f"{metric:>9}" for metric in METRICS))
    for name, results in rows.items():
        print(f"{name:10} " + " ".join(f"{results[m]:9.3f}" for m in METRICS))
