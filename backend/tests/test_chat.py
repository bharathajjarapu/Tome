import uuid
from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from pka.models import Conversation, Message, Role
from tests.conftest import Account
from tests.test_upload import make_project


def ask(client: TestClient, account: Account, projectid: str, question: str, **body: str) -> dict:
    posted = client.post(
        f"/projects/{projectid}/chat",
        json={"question": question, **body},
        headers=account.headers,
    )
    assert posted.status_code == 201, posted.text
    return posted.json()


def test_asking_starts_a_conversation_and_stores_the_question(
    client: TestClient, signup: Callable[..., Account], db: Session
) -> None:
    account = signup()
    projectid = make_project(client, account)
    answer = ask(client, account, projectid, "What is the retention window?")

    message = db.get(Message, uuid.UUID(answer["message_id"]))
    assert message.role == Role.user
    assert message.content == "What is the retention window?"
    assert str(message.conversation_id) == answer["conversation_id"]


def test_a_second_question_appends_to_the_same_conversation(
    client: TestClient, signup: Callable[..., Account], db: Session
) -> None:
    account = signup()
    projectid = make_project(client, account)
    first = ask(client, account, projectid, "First question")
    second = ask(
        client, account, projectid, "Second question", conversation_id=first["conversation_id"]
    )

    assert second["conversation_id"] == first["conversation_id"]
    assert len(db.scalars(select(Conversation)).all()) == 1


def test_another_teams_project_is_not_found(
    client: TestClient, signup: Callable[..., Account]
) -> None:
    owner = signup("owner@example.com")
    projectid = make_project(client, owner)
    stranger = signup("stranger@example.com")

    posted = client.post(
        f"/projects/{projectid}/chat", json={"question": "Hi"}, headers=stranger.headers
    )
    assert posted.status_code == 404


def test_a_conversation_from_another_project_is_ignored(
    client: TestClient, signup: Callable[..., Account], db: Session
) -> None:
    account = signup()
    first = make_project(client, account)
    second = make_project(client, account)
    started = ask(client, account, first, "First question")
    moved = ask(
        client, account, second, "Second question", conversation_id=started["conversation_id"]
    )

    assert moved["conversation_id"] != started["conversation_id"]
