from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from tests.conftest import Account
from tome.models import Document, IngestionJob, State


def upload(client: TestClient, account: Account, projectid: str, name: str, data: bytes):
    return client.post(
        f"/projects/{projectid}/documents",
        files={"file": (name, data, "application/octet-stream")},
        headers=account.headers,
    )


def make_project(client: TestClient, account: Account) -> str:
    return client.post("/projects", json={"name": "Docs"}, headers=account.headers).json()["id"]


def test_upload_queues_a_job(client: TestClient, signup: Callable[..., Account], db: Session):
    account = signup()
    projectid = make_project(client, account)

    r = upload(client, account, projectid, "notes.pdf", b"pretend pdf")
    assert r.status_code == 201
    body = r.json()
    assert body["state"] == State.uploaded
    assert body["filename"] == "notes.pdf"

    doc = db.scalars(select(Document)).one()
    assert doc.sha256 and doc.storage_key
    job = db.scalars(select(IngestionJob).where(IngestionJob.document_id == doc.id)).one()
    assert job.state is State.uploaded


def test_unsupported_type_rejected(client: TestClient, signup: Callable[..., Account], db: Session):
    account = signup()
    projectid = make_project(client, account)
    r = upload(client, account, projectid, "virus.exe", b"MZ")
    assert r.status_code == 415
    assert db.scalars(select(Document)).all() == []


def test_oversized_file_rejected(client: TestClient, signup: Callable[..., Account], db: Session):
    from tome.core.config import settings

    account = signup()
    projectid = make_project(client, account)
    big = b"x" * (settings.max_upload_bytes + 1)
    r = upload(client, account, projectid, "big.pdf", big)
    assert r.status_code == 413
    assert db.scalars(select(Document)).all() == []


def test_upload_to_another_team_is_not_found(client: TestClient, signup: Callable[..., Account]):
    owner = signup("owner@example.com")
    outsider = signup("outsider@example.com")
    projectid = make_project(client, owner)
    assert upload(client, outsider, projectid, "notes.pdf", b"x").status_code == 404
