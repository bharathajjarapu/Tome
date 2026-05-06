"""Cross-encoder reranking, in process. FastEmbed is already here for the embeddings."""

from dataclasses import replace
from functools import cache

from fastembed.rerank.cross_encoder import TextCrossEncoder

from pka.core.config import settings
from pka.rag.retrieve import Hit

MODEL = "Xenova/ms-marco-MiniLM-L-6-v2"


@cache
def encoder() -> TextCrossEncoder:
    return TextCrossEncoder(MODEL)


def rerank(query: str, hits: list[Hit]) -> list[Hit]:
    """Rescore the candidates against the query and keep the best `rerank_top_n`."""
    if not hits:
        return []
    scores = encoder().rerank(query, [hit.text for hit in hits])
    scored = [replace(hit, score=score) for hit, score in zip(hits, scores, strict=True)]
    scored.sort(key=lambda hit: hit.score, reverse=True)
    return scored[: settings.rerank_top_n]
