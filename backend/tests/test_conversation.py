from collections.abc import Callable

import pytest
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


@pytest.mark.parametrize("path", ["/conversations/not-a-uuid"])
def test_a_malformed_id_is_rejected(client: TestClient, path: str) -> None:
    assert client.get(path).status_code in (401, 422)
