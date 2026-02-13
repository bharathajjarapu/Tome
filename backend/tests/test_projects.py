from collections.abc import Callable

from fastapi.testclient import TestClient

from tests.conftest import Account


def test_create_and_list(client: TestClient, signup: Callable[..., Account]) -> None:
    account = signup()
    r = client.post("/projects", json={"name": "Handbook"}, headers=account.headers)
    assert r.status_code == 201
    assert r.json()["name"] == "Handbook"
    assert r.json()["team_id"] == str(account.team.id)

    listed = client.get("/projects", headers=account.headers).json()
    assert [p["name"] for p in listed] == ["Handbook"]


def test_list_excludes_other_teams(client: TestClient, signup: Callable[..., Account]) -> None:
    alice = signup("alice@example.com")
    bob = signup("bob@example.com")
    client.post("/projects", json={"name": "Alice only"}, headers=alice.headers)
    client.post("/projects", json={"name": "Bob only"}, headers=bob.headers)

    assert [p["name"] for p in client.get("/projects", headers=alice.headers).json()] == [
        "Alice only"
    ]
    assert [p["name"] for p in client.get("/projects", headers=bob.headers).json()] == ["Bob only"]




def test_blank_name_rejected(client: TestClient, signup: Callable[..., Account]) -> None:
    account = signup()
    r = client.post("/projects", json={"name": ""}, headers=account.headers)
    assert r.status_code == 422
