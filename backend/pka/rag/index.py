"""Chunk storage in Qdrant. One collection for everything, isolation by payload filter."""

import logging
import uuid
from functools import cache

from fastembed import SparseTextEmbedding, TextEmbedding
from fastembed.sparse.sparse_embedding_base import SparseEmbedding
from qdrant_client import QdrantClient, models

from pka.core.config import settings
from pka.ingestion.chunk import Chunk

log = logging.getLogger(__name__)

COLLECTION = "chunks"
DENSE, SPARSE = "dense", "sparse"
# Model and dimension change together.
DENSE_MODEL, DENSE_DIM = "BAAI/bge-small-en-v1.5", 384
SPARSE_MODEL = "Qdrant/bm25"
BATCH = 64


@cache
def client() -> QdrantClient:
    """One client per process. `location` takes a URL or `:memory:` for tests."""
    return QdrantClient(location=settings.qdrant_url)


@cache
def dense() -> TextEmbedding:
    return TextEmbedding(DENSE_MODEL)


@cache
def sparse() -> SparseTextEmbedding:
    return SparseTextEmbedding(SPARSE_MODEL)


@cache
def ensure_collection() -> None:
    """Create the collection and its payload indexes once per process."""
    if client().collection_exists(COLLECTION):
        return
    client().create_collection(
        COLLECTION,
        vectors_config={
            DENSE: models.VectorParams(size=DENSE_DIM, distance=models.Distance.COSINE)
        },
        sparse_vectors_config={SPARSE: models.SparseVectorParams()},
    )
    # Filters run on every query, so both keys are indexed. Local Qdrant ignores this.
    for key in ("team_id", "project_id", "document_id"):
        client().create_payload_index(COLLECTION, key, models.PayloadSchemaType.KEYWORD)


def index(chunks: list[Chunk]) -> int:
    """Replace a document's points with these. Returns how many were written."""
    if not chunks:
        return 0
    ensure_collection()
    forget(chunks[0].document_id)
    texts = [chunk.text for chunk in chunks]
    points = [
        models.PointStruct(
            id=str(chunk.chunk_id),
            vector={DENSE: dense_vector.tolist(), SPARSE: sparse_vector(sparse_embedding)},
            payload={
                "text": chunk.text,
                "team_id": str(chunk.team_id),
                "project_id": str(chunk.project_id),
                "document_id": str(chunk.document_id),
                "chunk_id": str(chunk.chunk_id),
                "document_name": chunk.document_name,
                "heading": chunk.heading,
                "section": chunk.section,
                "page": chunk.page,
            },
        )
        for chunk, dense_vector, sparse_embedding in zip(
            chunks,
            dense().embed(texts, batch_size=settings.model_batch),
            sparse().embed(texts),
            strict=True,
        )
    ]
    for start in range(0, len(points), BATCH):
        client().upsert(COLLECTION, points[start : start + BATCH])
    log.info("indexed %d chunks for document %s", len(points), chunks[0].document_id)
    return len(points)


def forget(documentid: uuid.UUID) -> None:
    """Drop every point belonging to one document."""
    ensure_collection()
    client().delete(COLLECTION, points_selector=match("document_id", documentid))


def count(documentid: uuid.UUID) -> int:
    ensure_collection()
    return client().count(COLLECTION, count_filter=match("document_id", documentid)).count


def match(key: str, value: uuid.UUID | str) -> models.Filter:
    """A payload filter on one key. Identifiers are stored as strings."""
    return models.Filter(
        must=[models.FieldCondition(key=key, match=models.MatchValue(value=str(value)))]
    )


def sparse_vector(embedding: SparseEmbedding) -> models.SparseVector:
    """FastEmbed returns numpy arrays; Qdrant wants plain lists."""
    return models.SparseVector(
        indices=embedding.indices.tolist(), values=embedding.values.tolist()
    )
