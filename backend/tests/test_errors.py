import logging
from collections.abc import Callable

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.conftest import Account
from tests.test_worker import queue
from tome.core import errors
from tome.worker import process_job


def test_a_known_failure_uses_the_error_shape(
    client: TestClient, signup: Callable[..., Account]
) -> None:
    r = client.get("/projects", headers={"Authorization": "Bearer nonsense"})
    assert r.status_code == 401
    assert r.json() == {"error": {"code": "unauthorized", "message": "Not authenticated"}}
    assert r.headers["WWW-Authenticate"] == "Bearer"


def test_invalid_input_is_not_echoed_back(client: TestClient) -> None:
    r = client.post("/auth/register", json={"email": "not-an-email", "password": "hunter2"})
    assert r.status_code == 422
    assert r.json()["error"]["message"] == "Invalid request"
    assert "hunter2" not in r.text


def test_an_unexpected_error_hides_its_detail(caplog) -> None:
    app = FastAPI()
    errors.install(app)

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("postgresql://user:secret@localhost/tome")

    with TestClient(app, raise_server_exceptions=False) as unsafe:
        r = unsafe.get("/boom")

    assert r.status_code == 500
    assert r.json() == {
        "error": {"code": "internal_server_error", "message": "Internal server error"}
    }
    assert "secret" not in r.text
    assert "secret" in caplog.text


def test_a_failing_ingestion_logs_both_ids(
    client: TestClient, signup: Callable[..., Account], db: Session, caplog
) -> None:
    job = queue(client, signup(), "broken.pdf", b"%PDF-1.4 not a pdf", db)
    with caplog.at_level(logging.ERROR):
        process_job(job.id)

    assert str(job.id) in caplog.text
    assert str(job.document_id) in caplog.text


def test_an_unknown_route_uses_the_error_shape(client: TestClient) -> None:
    r = client.get("/no-such-route")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"
