"""Retrieval on a document with enough sections for the wrong one to win."""

import uuid

import pytest

from pka.ingestion.chunk import split
from pka.rag import index
from pka.rag.context import build

TEAM, PROJECT = uuid.uuid4(), uuid.uuid4()

HANDBOOK = """# Engineering Handbook

## Onboarding

New engineers get a laptop on their first day and a mentor for their first month. Ask the mentor
for access to the staging environment; production access is granted after the first review.

## Deployments

Deploy to production on any weekday before 16:00. Friday deployments need written approval from
the on-call engineer. Every deployment runs the migration step first and is rolled back with the
previous release tag.

## Incidents

Page the on-call engineer after fifteen minutes without an acknowledgement. Write the incident
report within two working days and link it from the incident channel.

## Security

Rotate service credentials every ninety days. Secrets live in the vault, never in the repository,
and a leaked credential is revoked before anything else happens.

## Expenses

Submit expenses by the fifth of the following month. Anything above five hundred euros needs a
manager's approval before the purchase, not after it.

## Exam vouchers

The training budget covers the AZ-900, DP-900 and MS-900 exam vouchers once per engineer.

## Time off

Book holiday at least two weeks ahead. Sick leave needs no notice, but tell the team channel the
same morning so the standup can be covered.
"""

QUESTIONS = {
    "When can we deploy to production?": "Deployments",
    "How often do we rotate credentials?": "Security",
    "What is the deadline for submitting expenses?": "Expenses",
    "How long before someone is paged?": "Incidents",
    # A question in prose against a passage that is mostly codes: the reranker scores this
    # kind of match low, which is what the floor has to leave room for.
    "Which exam vouchers does the company pay for?": "Exam vouchers",
}


@pytest.fixture(autouse=True)
def seeded() -> None:
    index.index(
        split(
            HANDBOOK,
            team_id=TEAM,
            project_id=PROJECT,
            document_id=uuid.uuid4(),
            document_name="handbook.md",
        )
    )


def test_each_question_lands_on_its_own_section() -> None:
    for question, section in QUESTIONS.items():
        context = build(question, TEAM, PROJECT)
        assert context.enough, question
        assert context.hits[0].section.endswith(section), question

    # The same floor that lets those through still refuses a question the handbook cannot answer.
    assert not build("what is the capital of Peru", TEAM, PROJECT).enough
