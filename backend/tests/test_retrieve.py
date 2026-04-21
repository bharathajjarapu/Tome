import uuid

import pytest

from app.ingestion.chunk import split
from app.rag import index
from app.rag.retrieve import retrieve

TEAM_A, PROJECT_A = uuid.uuid4(), uuid.uuid4()
TEAM_B, PROJECT_B = uuid.uuid4(), uuid.uuid4()

DOC_A = "# Retention\n\nArchived logs are kept for ninety days, then deleted.\n"
DOC_B = "# Espresso\n\nThe espresso machine on floor two needs descaling monthly.\n"


@pytest.fixture(autouse=True)
def seeded() -> None:
    for text, team, project in ((DOC_A, TEAM_A, PROJECT_A), (DOC_B, TEAM_B, PROJECT_B)):
        index.index(
            split(
                text,
                team_id=team,
                project_id=project,
                document_id=uuid.uuid4(),
                document_name="notes.md",
            )
        )


def test_a_question_finds_its_own_project() -> None:
    hits = retrieve("how long are logs kept", TEAM_A, PROJECT_A)
    assert hits
    assert "ninety days" in hits[0].text


def test_another_teams_content_never_comes_back() -> None:
    for query in ("descaling the espresso machine", "espresso", "how long are logs kept"):
        assert all("espresso" not in hit.text for hit in retrieve(query, TEAM_A, PROJECT_A))


def test_hits_carry_citation_metadata() -> None:
    hit = retrieve("retention", TEAM_A, PROJECT_A)[0]
    assert hit.document_name == "notes.md"
    assert hit.section == "Retention"
    assert uuid.UUID(hit.chunk_id)
    assert hit.score > 0


def test_the_filters_cannot_be_left_out() -> None:
    with pytest.raises(TypeError):
        retrieve("anything")  # type: ignore[call-arg]
