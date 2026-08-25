"""Chunk storage and retrieval. One collection for everything, isolation by metadata filter."""

import logging
import uuid
from collections.abc import Sequence
from functools import cache

from llama_index.core import VectorStoreIndex
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.schema import BaseNode
from llama_index.core.vector_stores import MetadataFilter, MetadataFilters
from llama_index.core.vector_stores.types import VectorStoreQueryMode
from llama_index.embeddings.fastembed import FastEmbedEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import QdrantClient, models

from pka.core.config import settings

log = logging.getLogger(__name__)

COLLECTION = "nodes"
# Nodes embedded and written per slice. Indexing a whole book in one call holds every
# vector in memory and reports nothing until it finishes.
BATCH = 128
# Reads 8192 tokens, so a chunk is never half-embedded. The -Q build is the same weights
# quantised to int8: a quarter of the size, and it ranked our sample identically.
DENSE_MODEL = "nomic-ai/nomic-embed-text-v1.5-Q"
# This model requires a marker on every passage and every query. FastEmbed does not add
# them, so an unprefixed passage embeds away from the question that is looking for it.
DOCUMENT, QUERY = "search_document: ", "search_query: "
SPARSE_MODEL = "Qdrant/bm25"

# Every query filters on these, so they are indexed rather than scanned. A node's document is
# LlamaIndex's own ref_doc_id, which is why it is not in the metadata we set.
SCOPED = ("team_id", "project_id", "ref_doc_id")


@cache
def client() -> QdrantClient:
    """One client per process. `location` takes a URL or `:memory:` for tests."""
    return QdrantClient(location=settings.qdrant_url)


class Embedding(FastEmbedEmbedding):
    """FastEmbed, with the prefixes the dense model needs."""

    def _get_text_embeddings(self, texts: list[str]) -> list[list[float]]:
        return super()._get_text_embeddings([DOCUMENT + text for text in texts])

    def _get_query_embedding(self, query: str) -> list[float]:
        return super()._get_query_embedding(QUERY + query)


@cache
def embedding() -> Embedding:
    return Embedding(model_name=DENSE_MODEL)


@cache
def store() -> QdrantVectorStore:
    return QdrantVectorStore(
        COLLECTION,
        client=client(),
        enable_hybrid=True,
        fastembed_sparse_model=SPARSE_MODEL,
        payload_indexes=[
            models.CreateFieldIndex(
                field_name=key, field_schema=models.PayloadSchemaType.KEYWORD
            ).model_dump()
            for key in SCOPED
        ],
    )


@cache
def index() -> VectorStoreIndex:
    return VectorStoreIndex.from_vector_store(store(), embed_model=embedding())


def add(nodes: Sequence[BaseNode]) -> int:
    """Index passages a slice at a time. Re-indexing a document means forgetting it first."""
    for start in range(0, len(nodes), BATCH):
        index().insert_nodes(list(nodes[start : start + BATCH]))
        log.info("indexed %d/%d nodes", min(start + BATCH, len(nodes)), len(nodes))
    return len(nodes)


def scope(team_id: uuid.UUID, project_id: uuid.UUID) -> MetadataFilters:
    return MetadataFilters(
        filters=[
            MetadataFilter(key="team_id", value=str(team_id)),
            MetadataFilter(key="project_id", value=str(project_id)),
        ]
    )


def retriever(team_id: uuid.UUID, project_id: uuid.UUID) -> VectorIndexRetriever:
    """The one way to read. Both ids are required, so an unscoped retriever cannot be built."""
    return VectorIndexRetriever(
        index=index(),
        vector_store_query_mode=VectorStoreQueryMode.HYBRID,
        similarity_top_k=settings.top_k,
        sparse_top_k=settings.top_k,
        filters=scope(team_id, project_id),
    )


def forget(document_id: uuid.UUID) -> None:
    """Drop every node of one document. Re-indexing calls this first."""
    if client().collection_exists(COLLECTION):
        store().delete(ref_doc_id=str(document_id))


def count(document_id: uuid.UUID) -> int:
    if not client().collection_exists(COLLECTION):
        return 0
    return client().count(
        COLLECTION,
        count_filter=models.Filter(
            must=[
                models.FieldCondition(
                    key="ref_doc_id", match=models.MatchValue(value=str(document_id))
                )
            ]
        ),
    ).count
