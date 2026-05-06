"""Turn retrieved chunks into prompt context, or say the documents do not cover the question."""

import uuid
from dataclasses import dataclass, field

from pka.core.config import settings
from pka.rag.rerank import rerank
from pka.rag.retrieve import Hit, retrieve


@dataclass(frozen=True, slots=True)
class Context:
    """The passages worth showing the model, and whether there are any."""

    text: str = ""
    hits: list[Hit] = field(default_factory=list)

    @property
    def enough(self) -> bool:
        return bool(self.hits)


def build(query: str, team_id: uuid.UUID, project_id: uuid.UUID) -> Context:
    """Retrieve, rerank, and drop anything the reranker scored below the floor."""
    kept = [hit for hit in rerank(query, retrieve(query, team_id, project_id))
            if hit.score >= settings.score_floor]
    if not kept:
        return Context()
    return Context(text="\n\n".join(_passage(number, hit) for number, hit in enumerate(kept, 1)),
                   hits=kept)


def _passage(number: int, hit: Hit) -> str:
    where = f"{hit.document_name} — {hit.section}" if hit.section else hit.document_name
    return f"[{number}] {where}\n{hit.text}"
