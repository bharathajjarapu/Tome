"""Parsed Markdown to indexable nodes. Sections stay separate; tables keep their column names."""

import re
import uuid
from collections.abc import Iterator
from functools import cache

from llama_index.core import Document
from llama_index.core.node_parser import MarkdownNodeParser, SentenceSplitter
from llama_index.core.schema import BaseNode, TextNode

from pka.core.config import settings

HEADING = re.compile(r"^\s{0,3}#{1,6}\s+(.*)$")
ROW = re.compile(r"^\s*\|.*\|\s*$")

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
        text=text,
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
    return SentenceSplitter(chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap)


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


def _table(rows: list[str]) -> Iterator[str]:
    """Split on row boundaries, repeating the header so every chunk can be read on its own."""
    header, body = rows[:2], rows[2:]
    size = sum(len(row) + 1 for row in header)
    chunk: list[str] = []
    used = size
    for row in body:
        if chunk and used + len(row) + 1 > settings.chunk_size:
            yield "\n".join(header + chunk)
            chunk, used = [], size
        chunk.append(row)
        used += len(row) + 1
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
