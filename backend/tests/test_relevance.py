"""Retrieval on a document with enough sections for the wrong one to win."""

import uuid

import pytest
from llama_index.core.schema import QueryBundle

from tome.ingestion.nodes import build
from tome.rag import store
from tome.rag.rerank import Reranker

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
    # A question in prose against a passage that is mostly codes: the hardest kind for a
    # cross-encoder, and the one an absolute score floor used to refuse.
    "Which exam vouchers does the company pay for?": "Exam vouchers",
}


@pytest.fixture(autouse=True)
def seeded() -> None:
    store.add(
        build(
            HANDBOOK,
            team_id=TEAM,
            project_id=PROJECT,
            document_id=uuid.uuid4(),
            document_name="handbook.md",
        )
    )


def best(question: str) -> str:
    """The passage the pipeline would put first: hybrid retrieval, then reranking."""
    found = store.retriever(TEAM, PROJECT).retrieve(question)
    ranked = Reranker().postprocess_nodes(found, QueryBundle(question))
    return str(ranked[0].node.metadata["section"])


def test_each_question_lands_on_its_own_section() -> None:
    for question, section in QUESTIONS.items():
        assert best(question).endswith(section), question


def test_an_unrelated_question_still_retrieves_something_to_judge() -> None:
    """Nothing is refused before the model sees it; that decision moved into the prompt."""
    assert store.retriever(TEAM, PROJECT).retrieve("what is the capital of Peru")
