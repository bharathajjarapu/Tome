"""Split parsed Markdown into chunks. A chunk never crosses a heading boundary."""

import re
import uuid
from collections.abc import Iterator
from dataclasses import dataclass

from app.core.config import settings

HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
PARAGRAPH = re.compile(r"\n\s*\n")


@dataclass(frozen=True, slots=True)
class Chunk:
    """One indexable passage and the metadata a citation needs."""

    text: str
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    project_id: uuid.UUID
    team_id: uuid.UUID
    document_name: str
    heading: str
    section: str
    # AnyDoc's Markdown carries no page markers, so this stays None until a parser supplies one.
    page: int | None = None


def split(
    text: str,
    *,
    team_id: uuid.UUID,
    project_id: uuid.UUID,
    document_id: uuid.UUID,
    document_name: str,
) -> list[Chunk]:
    """Cut a document into chunks, each tagged with where it came from."""
    chunks: list[Chunk] = []
    for heading, section, body in _sections(text):
        for passage in _pack(body, settings.chunk_size, settings.chunk_overlap):
            chunks.append(
                Chunk(
                    text=passage,
                    # Derived from the position, so re-indexing overwrites instead of duplicating.
                    chunk_id=uuid.uuid5(document_id, str(len(chunks))),
                    document_id=document_id,
                    project_id=project_id,
                    team_id=team_id,
                    document_name=document_name,
                    heading=heading,
                    section=section,
                )
            )
    return chunks


def _sections(text: str) -> Iterator[tuple[str, str, str]]:
    """Yield (heading, section path, body) once per heading, plus any preamble."""
    stack: list[str] = []
    heading = ""
    body: list[str] = []
    for line in text.splitlines():
        match = HEADING.match(line)
        if not match:
            body.append(line)
            continue
        if any(line.strip() for line in body):
            yield heading, " > ".join(stack), "\n".join(body)
        level, heading = len(match.group(1)), match.group(2).strip()
        del stack[level - 1 :]
        stack.append(heading)
        body = []
    if any(line.strip() for line in body):
        yield heading, " > ".join(stack), "\n".join(body)


def _pack(body: str, size: int, overlap: int) -> list[str]:
    """Greedily fill chunks up to `size`, repeating the tail of the previous one."""
    passages: list[str] = []
    current = ""
    for piece in _pieces(body, size):
        if current and len(current) + len(piece) + 2 > size:
            passages.append(current)
            current = current[-overlap:].lstrip() if overlap else ""
        current = f"{current}\n\n{piece}" if current else piece
    if current.strip():
        passages.append(current)
    return passages


def _pieces(body: str, size: int) -> Iterator[str]:
    """Paragraphs, with anything longer than one chunk cut down to fit."""
    for paragraph in PARAGRAPH.split(body):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        for start in range(0, len(paragraph), size):
            yield paragraph[start : start + size]
