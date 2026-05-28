from collections.abc import Callable

from fastapi.testclient import TestClient

from pka.models import Role
from tests.conftest import Account
from tests.test_chat import ask
from tests.test_stream import seed

QUESTION = "How long are logs kept?"


def test_a_full_exchange_reads_back_in_order(
    client: TestClient, signup: Callable[..., Account], fakellm: list[str]  # noqa: F811
) -> None:
    account = signup()
    projectid = seed(client, account)
    asked = ask(client, account, projectid, QUESTION)
    client.get(
        f"/projects/{projectid}/chat/stream",
        params={"message_id": asked["message_id"]},
        headers=account.headers,
    )
    ask(client, account, projectid, "And backups?", conversation_id=asked["conversation_id"])

    read = client.get(
        f"/conversations/{asked['conversation_id']}", headers=account.headers
    ).json()
    assert [m["role"] for m in read["messages"]] == [Role.user, Role.assistant, Role.user]
    assert read["messages"][0]["content"] == QUESTION
    assert read["messages"][1]["citations"][0]["section"] == "Retention"
    assert read["messages"][2]["citations"] == []


def test_another_teams_conversation_is_not_found(
    client: TestClient, signup: Callable[..., Account]
) -> None:
    owner = signup("owner@example.com")
    projectid = client.post(
        "/projects", json={"name": "Docs"}, headers=owner.headers
    ).json()["id"]
    conversationid = ask(client, owner, projectid, "Mine")["conversation_id"]
    stranger = signup("stranger@example.com")

    got = client.get(f"/conversations/{conversationid}", headers=stranger.headers)
    assert got.status_code == 404


def test_an_unknown_conversation_is_not_found(
    client: TestClient, signup: Callable[..., Account]
) -> None:
    import uuid

    got = client.get(f"/conversations/{uuid.uuid4()}", headers=signup().headers)
    assert got.status_code == 404




def test_conversations_are_listed_newest_first_with_their_opening_question(
    client: TestClient, signup: Callable[..., Account]
) -> None:
    account = signup()
    projectid = client.post(
        "/projects", json={"name": "Docs"}, headers=account.headers
    ).json()["id"]
    first = ask(client, account, projectid, "First question")
    ask(client, account, projectid, "Follow-up", conversation_id=first["conversation_id"])
    second = ask(client, account, projectid, "Second question")

    listed = client.get(f"/projects/{projectid}/conversations", headers=account.headers).json()
    assert [row["title"] for row in listed] == ["Second question", "First question"]
    assert [row["id"] for row in listed] == [
        second["conversation_id"],
        first["conversation_id"],
    ]


def test_another_teams_conversations_cannot_be_listed(
    client: TestClient, signup: Callable[..., Account]
) -> None:
    owner = signup("owner@example.com")
    projectid = client.post(
        "/projects", json={"name": "Docs"}, headers=owner.headers
    ).json()["id"]
    stranger = signup("stranger@example.com")

    got = client.get(f"/projects/{projectid}/conversations", headers=stranger.headers)
    assert got.status_code == 404
