from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from pka import storage
from pka.models import Document, IngestionJob, State
from tests.conftest import Account
from tests.test_upload import make_project, upload


def test_list_shows_state(client: TestClient, signup: Callable[..., Account]) -> None:
    account = signup()
    projectid = make_project(client, account)
    upload(client, account, projectid, "a.pdf", b"x")
    upload(client, account, projectid, "b.docx", b"y")

    listed = client.get(f"/projects/{projectid}/documents", headers=account.headers).json()
    assert [d["filename"] for d in listed] == ["a.pdf", "b.docx"]
    assert {d["state"] for d in listed} == {State.uploaded}


def test_status_reports_failure(
    client: TestClient, signup: Callable[..., Account], db: Session
) -> None:
    account = signup()
    projectid = make_project(client, account)
    docid = upload(client, account, projectid, "a.pdf", b"x").json()["id"]

    doc = db.scalars(select(Document)).one()
    doc.state = State.failed
    doc.error = "parser returned nothing"
    db.commit()

    body = client.get(f"/documents/{docid}/status", headers=account.headers).json()
    assert body["state"] == State.failed
    assert body["error"] == "parser returned nothing"


def test_delete_removes_file_and_rows(
    client: TestClient, signup: Callable[..., Account], db: Session
) -> None:
    account = signup()
    projectid = make_project(client, account)
    docid = upload(client, account, projectid, "a.pdf", b"x").json()["id"]
    key = db.scalars(select(Document)).one().storage_key

    assert client.delete(f"/documents/{docid}", headers=account.headers).status_code == 204
    db.expunge_all()
    assert db.scalars(select(Document)).all() == []
    assert db.scalars(select(IngestionJob)).all() == []
    assert not storage.path(key).exists()


def test_reads_are_not_found_across_teams(
    client: TestClient, signup: Callable[..., Account]
) -> None:
    owner = signup("owner@example.com")
    outsider = signup("outsider@example.com")
    projectid = make_project(client, owner)
    docid = upload(client, owner, projectid, "a.pdf", b"x").json()["id"]

    assert client.get(
        f"/projects/{projectid}/documents", headers=outsider.headers
    ).status_code == 404
    assert client.get(f"/documents/{docid}/status", headers=outsider.headers).status_code == 404
    assert client.delete(f"/documents/{docid}", headers=outsider.headers).status_code == 404
