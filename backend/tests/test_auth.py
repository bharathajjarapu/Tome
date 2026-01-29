from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import read_token
from app.models import Membership, User

CREDS = {"email": "sam@example.com", "password": "correct-horse"}


def test_register_then_login(client: TestClient, db: Session) -> None:
    r = client.post("/auth/register", json=CREDS)
    assert r.status_code == 201
    assert r.json()["email"] == CREDS["email"]
    assert "password" not in r.text and "hash" not in r.text

    r = client.post("/auth/login", json=CREDS)
    assert r.status_code == 200
    token = r.json()["access_token"]

    user = db.scalars(select(User).where(User.email == CREDS["email"])).one()
    assert read_token(token) == user.id


def test_register_creates_personal_team(client: TestClient, db: Session) -> None:
    client.post("/auth/register", json=CREDS)
    user = db.scalars(select(User).where(User.email == CREDS["email"])).one()
    assert db.scalars(select(Membership).where(Membership.user_id == user.id)).one()


def test_duplicate_email_conflicts(client: TestClient) -> None:
    client.post("/auth/register", json=CREDS)
    assert client.post("/auth/register", json=CREDS).status_code == 409


def test_wrong_password_unauthorised(client: TestClient) -> None:
    client.post("/auth/register", json=CREDS)
    r = client.post("/auth/login", json={**CREDS, "password": "wrong-password"})
    assert r.status_code == 401


def test_unknown_email_unauthorised(client: TestClient) -> None:
    r = client.post("/auth/login", json={"email": "nobody@example.com", "password": "whatever!"})
    assert r.status_code == 401


def test_short_password_rejected(client: TestClient) -> None:
    assert client.post("/auth/register", json={**CREDS, "password": "short"}).status_code == 422
