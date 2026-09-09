"""Parsed Markdown to indexable nodes. Sections stay separate; tables keep their column names."""

import re
import uuid
from collections.abc import Iterator
from functools import cache

from llama_index.core import Document
from llama_index.core.node_parser import MarkdownNodeParser, SentenceSplitter
from llama_index.core.schema import BaseNode, TextNode
from llama_index.core.utils import get_tokenizer

from tome.core.config import settings

HEADING = re.compile(r"^\s{0,3}#{1,6}\s+(.*)$")
# A converter emits one of these per picture. Indexed, they bury the real text.
IMAGE = re.compile(
    r"^\s*(?:!?\[[^\]]*\]\([^)]*\)|[\w./-]+\.(?:png|jpe?g|gif|svg|webp|bmp))\s*$", re.IGNORECASE
)
# Sentence boundary, kept zero-width so rejoining the pieces reproduces the text exactly.
# nltk's tokenizer needs a data file it refuses to read when hardlinked, which is how uv
# builds a virtualenv. A regex keeps that whole dependency out of the ingestion path.
SENTENCE = re.compile(r"(?<=[.!?])(?=\s)")
ROW = re.compile(r"^\s*\|.*\|\s*$")
NUMBER = re.compile(r"^[\d.,%+\-/ ]*\d[\d.,%+\-/ ]*$")

# A PDF table often carries a title row and a units row above the real column names, so the
# header block is found rather than assumed. Four rows is more than any of them need.
MAX_HEADER = 4

# Scope ids are uuids: noise in an embedding and in the model's context. Name and section are not.
HIDDEN = ["team_id", "project_id"]


def build(
    text: str,
    *,
    team_id: uuid.UUID,
    project_id: uuid.UUID,
    document_id: uuid.UUID,
    document_name: str,
) -> list[BaseNode]:
    """Cut a document into nodes, each tagged with where it came from."""
    # The id is LlamaIndex's ref_doc_id, which is how the store forgets one document.
    document = Document(
        text=_strip(text),
        id_=str(document_id),
        metadata={
            "team_id": str(team_id),
            "project_id": str(project_id),
            "document_name": document_name,
        },
    )
    nodes: list[BaseNode] = []
    for section in MarkdownNodeParser().get_nodes_from_documents([document]):
        heading, body = _heading(section.get_content())
        if not body.strip():
            continue
        section.metadata["section"] = _section(section.metadata.pop("header_path", ""), heading)
        nodes.extend(_clone(section, piece) for piece in _pieces(body))
    return nodes


@cache
def _splitter() -> SentenceSplitter:
    return SentenceSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        chunking_tokenizer_fn=SENTENCE.split,
    )


def _strip(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if not IMAGE.match(line))


def _heading(text: str) -> tuple[str, str]:
    """Split a section into its own heading and the rest. The heading lives in metadata instead."""
    first, _, rest = text.partition("\n")
    found = HEADING.match(first)
    return (found.group(1).strip(), rest) if found else ("", text)


def _section(path: str, heading: str) -> str:
    parts = [part for part in path.split("/") if part]
    if heading:
        parts.append(heading)
    return " > ".join(parts)


def _pieces(body: str) -> Iterator[str]:
    rows = [line for line in body.splitlines() if line.strip()]
    if len(rows) > 2 and all(ROW.match(row) for row in rows):
        yield from _table(rows)
    else:
        yield from _splitter().split_text(body)


def _cells(row: str) -> list[str]:
    return [cell.strip() for cell in row.strip().strip("|").split("|")]


def _isdata(row: str) -> bool:
    """A data row is mostly numbers. Titles, units and column names are words."""
    filled = [cell for cell in _cells(row) if cell and not set(cell) <= {"-", ":"}]
    if not filled:
        return False
    return sum(bool(NUMBER.match(cell)) for cell in filled) * 2 >= len(filled)


def _headroom(rows: list[str]) -> int:
    """How many leading rows describe the table rather than fill it."""
    for position, row in enumerate(rows[:MAX_HEADER]):
        if _isdata(row):
            return max(position, 2)
    return min(len(rows) - 1, MAX_HEADER)


def _table(rows: list[str]) -> Iterator[str]:
    """Split on row boundaries, repeating the header so every chunk can be read on its own."""
    count = get_tokenizer()
    edge = _headroom(rows)
    header, body = rows[:edge], rows[edge:]
    # Budgeted in tokens like the prose splitter: a table row packs far more characters
    # into a token than prose does, so counting characters here overfills the chunk.
    size = sum(len(count(row)) for row in header)
    chunk: list[str] = []
    used = size
    for row in body:
        length = len(count(row))
        if chunk and used + length > settings.chunk_size:
            yield "\n".join(header + chunk)
            chunk, used = [], size
        chunk.append(row)
        used += length
    if chunk:
        yield "\n".join(header + chunk)


def _clone(section: BaseNode, text: str) -> TextNode:
    return TextNode(
        text=text,
        metadata=dict(section.metadata),
        relationships=dict(section.relationships),
        excluded_embed_metadata_keys=HIDDEN,
        excluded_llm_metadata_keys=HIDDEN,
    )
