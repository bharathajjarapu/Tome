"""Parsed Markdown to indexable nodes: the metadata a citation needs, and tables kept readable."""

import uuid

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
        assert len(node.text) <= settings.chunk_size * 2


def test_the_whole_table_survives_the_split() -> None:
    rows = "\n".join(node.text for node in nodes(TABLE))
    for wanted in ("|1|COMPANY1|", "|200|COMPANY200|", "|399|COMPANY399|"):
        assert wanted in rows
