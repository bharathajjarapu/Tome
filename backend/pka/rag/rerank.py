"""Cross-encoder reranking, in process. FastEmbed is already here for the embeddings."""

from functools import cache

from fastembed.rerank.cross_encoder import TextCrossEncoder
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.schema import MetadataMode, NodeWithScore, QueryBundle
from pydantic import Field

from pka.core.config import settings

MODEL = "Xenova/ms-marco-MiniLM-L-6-v2"


@cache
def encoder() -> TextCrossEncoder:
    """One model per process; loading it is the expensive part."""
    return TextCrossEncoder(MODEL)


class Reranker(BaseNodePostprocessor):
    """Rescore the candidates against the query and keep the best few."""

    top_n: int = Field(default_factory=lambda: settings.rerank_top_n)

    def _postprocess_nodes(
        self, nodes: list[NodeWithScore], query_bundle: QueryBundle | None = None
    ) -> list[NodeWithScore]:
        if not nodes or query_bundle is None:
            return nodes
        # The name and section travel with the text, which is what the encoder sees.
        texts = [node.node.get_content(MetadataMode.EMBED) for node in nodes]
        scores = encoder().rerank(query_bundle.query_str, texts, batch_size=settings.rerank_batch)
        for node, score in zip(nodes, scores, strict=True):
            node.score = score
        nodes.sort(key=lambda node: node.score or 0.0, reverse=True)
        return nodes[: self.top_n]
