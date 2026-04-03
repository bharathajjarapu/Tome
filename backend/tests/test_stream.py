import json
import uuid
from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient

from app.ingestion.chunk import split
from app.rag import generate, index
from tests.conftest import Account
from tests.test_chat import ask
from tests.test_upload import make_project

ANSWER = ["Archived ", "logs ", "are ", "kept ", "for ", "ninety ", "days."]
DOC = "# Retention\n\nArchived logs are kept for ninety days, then deleted.\n"


@pytest.fixture
def fakellm(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Records the prompts it was given and returns fixed tokens."""
    calls: list[str] = []

    def stream(question: str, context: str) -> Iterator[str]:
        calls.append(question)
        yield from ANSWER

    monkeypatch.setattr(generate, "stream", stream)
    return calls


def seed(client: TestClient, account: Account) -> str:
    projectid = make_project(client, account)
    project = client.get(f"/projects/{projectid}", headers=account.headers).json()
    index.index(
        split(
            DOC,
            team_id=uuid.UUID(project["team_id"]),
            project_id=uuid.UUID(projectid),
            document_id=uuid.uuid4(),
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
    assert cited["section"] == "Retention"
    assert cited["page"] is None
    assert "ninety days" in cited["snippet"]


def test_a_generation_failure_ends_with_an_error_event(
    client: TestClient, signup: Callable[..., Account], monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(question: str, context: str) -> Iterator[str]:
        raise RuntimeError("upstream is down")
        yield

    monkeypatch.setattr(generate, "stream", boom)
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
