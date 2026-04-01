import uuid

import pytest

from app.ingestion.chunk import split
from app.rag import index
from app.rag.context import build

TEAM, PROJECT = uuid.uuid4(), uuid.uuid4()
DOC = """# Retention

Archived logs are kept for ninety days, then deleted.

# Kitchen

The espresso machine on floor two needs descaling monthly.
"""


@pytest.fixture(scope="module", autouse=True)
def seeded() -> None:
    index.index(
        split(
            DOC,
            team_id=TEAM,
            project_id=PROJECT,
            document_id=uuid.uuid4(),
            document_name="handbook.md",
        )
    )


def test_the_best_passage_comes_first() -> None:
    context = build("how long are archived logs kept", TEAM, PROJECT)
    assert context.enough
    assert "ninety days" in context.hits[0].text
    assert context.text.startswith("[1] handbook.md — Retention")


def test_an_unrelated_question_is_flagged_as_uncovered() -> None:
    context = build("what is the mortgage interest rate in Portugal", TEAM, PROJECT)
    assert not context.enough
    assert context.text == ""


def test_no_more_than_the_configured_number_of_passages(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "rerank_top_n", 1)
    assert len(build("logs", TEAM, PROJECT).hits) == 1
