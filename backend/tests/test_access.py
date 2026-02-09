from collections.abc import Callable

from fastapi.testclient import TestClient

from app.core.security import create_token
from tests.conftest import Account


def test_no_token_unauthorised(
    client: TestClient, signup: Callable[..., Account], newproject: Callable[..., object]
) -> None:
    account = signup()
    project = newproject(account.team)
    assert client.get(f"/projects/{project.id}").status_code == 401


def test_garbage_token_unauthorised(client: TestClient) -> None:
    headers = {"Authorization": "Bearer not-a-token"}
    r = client.get("/projects/00000000-0000-0000-0000-000000000000", headers=headers)
    assert r.status_code == 401


def test_expired_token_unauthorised(
    client: TestClient, signup: Callable[..., Account], monkeypatch
) -> None:
    from app.core import security

    account = signup()
    monkeypatch.setattr(security.settings, "jwt_ttl_minutes", -1)
    expired = create_token(account.user.id)
    r = client.get(
        "/projects/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {expired}"},
    )
    assert r.status_code == 401


def test_member_reads_own_project(
    client: TestClient, signup: Callable[..., Account], newproject: Callable[..., object]
) -> None:
    account = signup()
    project = newproject(account.team)
    r = client.get(f"/projects/{project.id}", headers=account.headers)
    assert r.status_code == 200
    assert r.json()["name"] == "Docs"


def test_other_teams_project_is_not_found(
    client: TestClient, signup: Callable[..., Account], newproject: Callable[..., object]
) -> None:
    owner = signup("owner@example.com")
    outsider = signup("outsider@example.com")
    project = newproject(owner.team)
    r = client.get(f"/projects/{project.id}", headers=outsider.headers)
    assert r.status_code == 404
