"""Reranking: the passage that answers the question comes first, and only the best survive."""

from llama_index.core.schema import NodeWithScore, QueryBundle, TextNode

from tome.rag.rerank import Reranker

PASSAGES = [
    "The espresso machine on floor two needs descaling monthly.",
    "Archived logs are kept for ninety days, then deleted.",
    "New engineers get a laptop on their first day.",
]


def scored(texts: list[str]) -> list[NodeWithScore]:
    return [NodeWithScore(node=TextNode(text=text), score=0.5) for text in texts]


def test_the_passage_that_answers_the_question_comes_first() -> None:
    ranked = Reranker().postprocess_nodes(
        scored(PASSAGES), QueryBundle("how long are archived logs kept")
    )
    assert "ninety days" in ranked[0].node.text


def test_only_the_configured_number_survives() -> None:
    ranked = Reranker(top_n=2).postprocess_nodes(scored(PASSAGES), QueryBundle("logs"))
    assert len(ranked) == 2
