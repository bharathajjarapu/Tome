"""Parsed Markdown to indexable nodes: the metadata a citation needs, and tables kept readable."""

import uuid

from llama_index.core.schema import MetadataMode
from llama_index.core.utils import get_tokenizer

from pka.core.config import settings
from pka.ingestion.nodes import build

TEAM, PROJECT, DOCUMENT = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()

HANDBOOK = """# Engineering Handbook

## Deployments

Deploy to production on any weekday before 16:00.

## Security

Rotate service credentials every ninety days.
"""

HEADER = "|S.No|Company|Salary|CSE|\n|---|---|---|---|"
TABLE = "# Placements\n\n" + HEADER + "\n" + "\n".join(
    f"|{n}|COMPANY{n}|{n}.50|{n}|" for n in range(1, 400)
)


def nodes(text: str) -> list:
    return build(
        text,
        team_id=TEAM,
        project_id=PROJECT,
        document_id=DOCUMENT,
        document_name="doc.md",
    )


def test_every_node_carries_its_scope_and_source() -> None:
    for node in nodes(HANDBOOK):
        assert node.metadata["team_id"] == str(TEAM)
        assert node.metadata["project_id"] == str(PROJECT)
        assert node.metadata["document_name"] == "doc.md"
        assert node.ref_doc_id == str(DOCUMENT)


def test_a_node_knows_which_section_it_came_from() -> None:
    sections = {node.metadata["section"] for node in nodes(HANDBOOK)}
    assert any("Deployments" in section for section in sections)
    assert any("Security" in section for section in sections)


def test_a_section_never_mixes_with_another() -> None:
    for node in nodes(HANDBOOK):
        if "Deployments" in node.metadata["section"]:
            assert "credentials" not in node.text


def test_a_long_table_is_split_on_rows_and_keeps_its_header() -> None:
    built = nodes(TABLE)
    assert len(built) > 1, "a 400-row table has to be split"
    for node in built:
        assert node.text.startswith(HEADER), "every chunk needs the column names"
        assert node.text.rstrip().endswith("|"), "no row may be cut in half"
        # Budgeted in tokens, and a chunk may overshoot by the one row that tipped it over.
        assert len(get_tokenizer()(node.text)) <= settings.chunk_size * 2


def test_the_whole_table_survives_the_split() -> None:
    rows = "\n".join(node.text for node in nodes(TABLE))
    for wanted in ("|1|COMPANY1|", "|200|COMPANY200|", "|399|COMPANY399|"):
        assert wanted in rows


TITLED = "# Placements\n\n" + "\n".join(
    [
        "|||PLACEMENT REPORT 2025|",
        "|---|---|---|---|",
        "|||Rs. per annum|",
        "|S.No|Company|Salary|Seats|",
    ]
    + [f"|{n}|COMPANY{n}|{n}.50|{n}|" for n in range(1, 400)]
)


def test_a_table_keeps_the_column_names_even_when_a_title_sits_above_them() -> None:
    """A PDF table often has a title and a units row above the real header."""
    for node in nodes(TITLED):
        assert "PLACEMENT REPORT 2025" in node.text
        assert "|S.No|Company|Salary|Seats|" in node.text


PROSE = "# Chapter One\n\n" + "The lamplighter walked the quiet street. " * 200

DECK = """# Deck

preencoded.png

**What is the Innovation Hub?**

preencoded.png

We bridge the gap between academia and industry.
"""


def test_a_long_passage_is_split_into_several_nodes() -> None:
    """One oversized paragraph must still chunk. Sentence splitting cannot need a data download."""
    pieces = nodes(PROSE)
    assert len(pieces) > 1
    # Nothing may be dropped on the way through the splitter.
    assert sum(piece.get_content().count("lamplighter") for piece in pieces) >= 200


def test_image_placeholders_never_reach_a_node() -> None:
    """Converters emit a bare image filename per picture. Indexing those buries the real text."""
    text = " ".join(piece.get_content() for piece in nodes(DECK))
    assert "preencoded" not in text
    assert "academia and industry" in text


# The embedding model reads 512 of its own tokens and silently drops the rest. Its tokenizer
# runs up to about 1.2 tokens per tiktoken token, so this is the safe budget measured here.
EMBED_BUDGET = 430


def test_no_node_is_longer_than_the_embedding_model_reads() -> None:
    """Text past the model's window contributes nothing to the vector: it may as well not exist."""
    count = get_tokenizer()
    for text in (HANDBOOK, PROSE, TABLE, DECK):
        for node in nodes(text):
            assert len(count(node.get_content(MetadataMode.EMBED))) <= EMBED_BUDGET
