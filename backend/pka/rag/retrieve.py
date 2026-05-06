"""The only path to Qdrant for reading. Team and project filters are not optional."""

import uuid
from dataclasses import dataclass

from qdrant_client import models

from pka.core.config import settings
from pka.rag.index import (
    COLLECTION,
    DENSE,
    SPARSE,
    client,
    dense,
    ensure_collection,
    sparse,
    sparse_vector,
)


@dataclass(frozen=True, slots=True)
class Hit:
    """A retrieved chunk with everything a citation needs."""

    text: str
    score: float
    document_id: uuid.UUID
    chunk_id: str
    document_name: str
    section: str
    page: int | None


def retrieve(query: str, team_id: uuid.UUID, project_id: uuid.UUID) -> list[Hit]:
    """Hybrid search inside one project. Omitting either id is a TypeError, not a leak."""
    ensure_collection()
    scope = models.Filter(
        must=[
            models.FieldCondition(key="team_id", match=models.MatchValue(value=str(team_id))),
            models.FieldCondition(key="project_id", match=models.MatchValue(value=str(project_id))),
        ]
    )
    dense_query = next(iter(dense().query_embed(query))).tolist()
    sparse_query = sparse_vector(next(iter(sparse().query_embed(query))))
    found = client().query_points(
        COLLECTION,
        prefetch=[
            models.Prefetch(
                query=dense_query, using=DENSE, limit=settings.top_k, filter=scope
            ),
            models.Prefetch(
                query=sparse_query, using=SPARSE,
                limit=settings.top_k, filter=scope,
            ),
        ],
        query=models.FusionQuery(fusion=models.Fusion.RRF),
        limit=settings.top_k,
        with_payload=True,
    )
    return [_hit(point) for point in found.points]


def _hit(point: models.ScoredPoint) -> Hit:
    payload = point.payload or {}
    return Hit(
        text=payload["text"],
        score=point.score,
        document_id=uuid.UUID(payload["document_id"]),
        chunk_id=payload["chunk_id"],
        document_name=payload["document_name"],
        section=payload["section"],
        page=payload["page"],
    )
