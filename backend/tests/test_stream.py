import json
import uuid
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from pka.ingestion.nodes import build
from pka.models import Citation, Message, Role
from pka.rag import chat as ragchat
from pka.rag import store
from pka.services import answer
from tests.conftest import ANSWER, Account
from tests.test_chat import ask
from tests.test_upload import make_project, upload

DOC = "# Retention\n\nArchived logs are kept for ninety days, then deleted.\n"



def seed(client: TestClient, account: Account) -> str:
    """A project holding one indexed document, without running the worker."""
    projectid = make_project(client, account)
    project = client.get(f"/projects/{projectid}", headers=account.headers).json()
    documentid = upload(client, account, projectid, "handbook.md", DOC.encode()).json()["id"]
    store.add(
        build(
            DOC,
            team_id=uuid.UUID(project["team_id"]),
            project_id=uuid.UUID(projectid),
            document_id=uuid.UUID(documentid),
            document_name="handbook.md",
        )
    )
    return projectid


def events(body: str) -> list[str]:
    lines = body.splitlines()
    return [line.removeprefix("event: ") for line in lines if line.startswith("event: ")]


def data(body: str, event: str) -> list[str]:
    frames = body.split("\n\n")
    return [f.split("data: ", 1)[1] for f in frames if f.startswith(f"event: {event}\n")]


def stream(client: TestClient, account: Account, projectid: str, question: str) -> str:
    posted = ask(client, account, projectid, question)
    got = client.get(
        f"/projects/{projectid}/chat/stream",
        params={"message_id": posted["message_id"]},
        headers=account.headers,
    )
    assert got.status_code == 200
    assert got.headers["content-type"].startswith("text/event-stream")
    return got.text


def test_the_event_order_is_fixed(
    client: TestClient, signup: Callable[..., Account], fakellm: list[str]
) -> None:
    account = signup()
    body = stream(client, account, seed(client, account), "How long are logs kept?")
    order = events(body)

    assert order[0] == "message_start"
    assert order[-1] == "message_end"
    assert set(order[1:-1]) == {"token", "citation"}
    assert order.index("citation") > max(i for i, e in enumerate(order) if e == "token")


def test_tokens_concatenate_to_the_answer(
    client: TestClient, signup: Callable[..., Account], fakellm: list[str]
) -> None:
    account = signup()
    body = stream(client, account, seed(client, account), "How long are logs kept?")
    assert "".join(json.loads(d)["text"] for d in data(body, "token")) == "".join(ANSWER)


def test_citations_carry_their_source(
    client: TestClient, signup: Callable[..., Account], fakellm: list[str]
) -> None:
    account = signup()
    body = stream(client, account, seed(client, account), "How long are logs kept?")
    cited = json.loads(data(body, "citation")[0])

    assert cited["document_name"] == "handbook.md"
    assert cited["section"].endswith("Retention")
    assert cited["page"] is None
    assert "ninety days" in cited["snippet"]


def test_a_generation_failure_ends_with_an_error_event(
    client: TestClient, signup: Callable[..., Account], monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom() -> object:
        raise RuntimeError("upstream is down")

    monkeypatch.setattr(ragchat, "llm", boom)
    account = signup()
    body = stream(client, account, seed(client, account), "How long are logs kept?")

    assert events(body) == ["message_start", "error"]
    assert "upstream" not in body


def test_another_users_message_is_not_found(
    client: TestClient, signup: Callable[..., Account]
) -> None:
    owner = signup("owner@example.com")
    projectid = make_project(client, owner)
    posted = ask(client, owner, projectid, "Mine")
    stranger = signup("stranger@example.com")

    got = client.get(
        f"/projects/{projectid}/chat/stream",
        params={"message_id": posted["message_id"]},
        headers=stranger.headers,
    )
    assert got.status_code == 404


def test_the_answer_and_its_citations_are_stored(
    client: TestClient, signup: Callable[..., Account], fakellm: list[str], db: Session
) -> None:
    account = signup()
    stream(client, account, seed(client, account), "How long are logs kept?")

    stored = db.scalars(select(Message).where(Message.role == Role.assistant)).one()
    assert stored.content == "".join(ANSWER)
    cited = db.scalars(select(Citation).where(Citation.message_id == stored.id)).all()
    assert cited and all("ninety days" in c.snippet or c.snippet for c in cited)
    assert cited[0].section.endswith("Retention")


def test_an_uncovered_question_reaches_the_model_rather_than_a_threshold(
    client: TestClient, signup: Callable[..., Account], fakellm: list[str]
) -> None:
    """Refusing is the model's job now: it sees the passages and decides they do not answer."""
    account = signup()
    body = stream(client, account, seed(client, account), "What is the capital of Peru?")

    assert events(body)[0] == "message_start"
    assert events(body)[-1] == "message_end"
    assert fakellm, "the question must be put to the model"
    assert "capital of Peru" in fakellm[-1]


def test_a_follow_up_question_is_asked_with_the_conversation_in_view(
    client: TestClient, signup: Callable[..., Account], fakellm: list[str]
) -> None:
    account = signup()
    projectid = seed(client, account)
    first = ask(client, account, projectid, "How long are logs kept?")
    client.get(
        f"/projects/{projectid}/chat/stream",
        params={"message_id": first["message_id"]},
        headers=account.headers,
    )
    second = ask(
        client, account, projectid, "And after that?", conversation_id=first["conversation_id"]
    )
    fakellm.clear()
    client.get(
        f"/projects/{projectid}/chat/stream",
        params={"message_id": second["message_id"]},
        headers=account.headers,
    )

    # The follow-up cannot stand alone, so the earlier turn has to reach the model.
    assert any("How long are logs kept?" in prompt for prompt in fakellm)


def test_an_answer_cannot_be_answered_as_a_question(
    client: TestClient, signup: Callable[..., Account], fakellm: list[str], db: Session
) -> None:
    account = signup()
    projectid = seed(client, account)
    stream(client, account, projectid, "How long are logs kept?")
    reply = db.scalars(select(Message).where(Message.role == Role.assistant)).one()

    got = client.get(
        f"/projects/{projectid}/chat/stream",
        params={"message_id": str(reply.id)},
        headers=account.headers,
    )
    assert got.status_code == 404


def test_history_stops_at_the_question_being_answered(
    client: TestClient, signup: Callable[..., Account], fakellm: list[str], db: Session
) -> None:
    account = signup()
    projectid = seed(client, account)
    first = ask(client, account, projectid, "How long are logs kept?")
    ask(client, account, projectid, "And after that?", conversation_id=first["conversation_id"])

    thread = answer.history(
        db, uuid.UUID(first["conversation_id"]), uuid.UUID(first["message_id"])
    )
    assert thread == []


def test_a_question_is_answered_once(
    client: TestClient, signup: Callable[..., Account], fakellm: list[str]
) -> None:
    account = signup()
    projectid = seed(client, account)
    posted = ask(client, account, projectid, "How long are logs kept?")
    url = f"/projects/{projectid}/chat/stream"
    params = {"message_id": posted["message_id"]}

    client.get(url, params=params, headers=account.headers)
    assert client.get(url, params=params, headers=account.headers).status_code == 409
