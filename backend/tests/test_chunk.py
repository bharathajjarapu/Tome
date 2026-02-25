import uuid

from app.core.config import settings
from app.ingestion.chunk import Chunk, split

DOC = """# Handbook

Intro paragraph about the handbook.

## Onboarding

Ask for a laptop on day one.

### Accounts

Request access to the deploy tool.

## Support

Escalate to the on-call engineer.
"""

IDS = {
    "team_id": uuid.uuid4(),
    "project_id": uuid.uuid4(),
    "document_id": uuid.uuid4(),
    "document_name": "handbook.md",
}


def chunks() -> list[Chunk]:
    return split(DOC, **IDS)


def test_one_chunk_per_section() -> None:
    assert [c.heading for c in chunks()] == ["Handbook", "Onboarding", "Accounts", "Support"]


def test_a_chunk_never_spans_two_sections() -> None:
    for chunk in chunks():
        assert "on-call" not in chunk.text or chunk.heading == "Support"


def test_section_records_the_heading_path() -> None:
    accounts = next(c for c in chunks() if c.heading == "Accounts")
    assert accounts.section == "Handbook > Onboarding > Accounts"


def test_every_chunk_carries_its_metadata() -> None:
    for chunk in chunks():
        assert chunk.team_id == IDS["team_id"]
        assert chunk.project_id == IDS["project_id"]
        assert chunk.document_id == IDS["document_id"]
        assert chunk.document_name == "handbook.md"
        assert chunk.page is None
        assert chunk.text.strip()


def test_chunk_ids_are_stable_across_runs() -> None:
    assert [c.chunk_id for c in chunks()] == [c.chunk_id for c in chunks()]


def test_long_sections_are_split_with_overlap() -> None:
    body = "\n\n".join(f"Paragraph {n} of the long section." for n in range(200))
    parts = split(f"# Long\n\n{body}\n", **IDS)
    assert len(parts) > 1
    assert all(len(p.text) <= settings.chunk_size + settings.chunk_overlap for p in parts)
    assert parts[1].text.startswith(parts[0].text[-settings.chunk_overlap :].lstrip())
