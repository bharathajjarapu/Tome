from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from pka.core.config import settings
from pka.models import Document, IngestionJob, State
from pka.rag import store
from pka.worker import claim, process_job
from tests.conftest import Account
from tests.test_upload import make_project, upload

RUNBOOK = b"# Runbook\n\nRestart the ingestion worker before the database.\n"


def queue(
    client: TestClient, account: Account, name: str, data: bytes, db: Session
) -> IngestionJob:
    projectid = make_project(client, account)
    upload(client, account, projectid, name, data)
    return db.scalars(select(IngestionJob)).one()


def test_a_good_document_reaches_indexed(
    client: TestClient, signup: Callable[..., Account], db: Session
) -> None:
    job = queue(client, signup(), "runbook.md", RUNBOOK, db)
    process_job(job.id)

    db.expunge_all()
    doc = db.get(Document, job.document_id)
    assert doc.state == State.indexed
    assert doc.error is None
    assert db.get(IngestionJob, job.id).state == State.indexed
    assert store.count(doc.id) > 0


def test_a_parse_failure_is_recorded_and_leaves_no_chunks(
    client: TestClient, signup: Callable[..., Account], db: Session
) -> None:
    job = queue(client, signup(), "broken.pdf", b"%PDF-1.4 not a pdf", db)
    process_job(job.id)

    db.expunge_all()
    doc = db.get(Document, job.document_id)
    assert doc.state == State.failed
    assert "broken.pdf" in doc.error
    assert store.count(doc.id) == 0
    assert db.get(IngestionJob, job.id).attempts == 1


def test_failures_stop_retrying_at_the_cap(
    client: TestClient, signup: Callable[..., Account], db: Session
) -> None:
    job = queue(client, signup(), "broken.pdf", b"%PDF-1.4 not a pdf", db)
    for _ in range(settings.max_attempts):
        process_job(job.id)

    db.expunge_all()
    assert db.get(IngestionJob, job.id).state == State.failed


def test_reprocessing_keeps_the_chunk_count_stable(
    client: TestClient, signup: Callable[..., Account], db: Session
) -> None:
    job = queue(client, signup(), "runbook.md", RUNBOOK, db)
    process_job(job.id)
    first = store.count(job.document_id)
    process_job(job.id)
    assert store.count(job.document_id) == first


def test_claim_takes_the_queued_job_once(
    client: TestClient, signup: Callable[..., Account], db: Session
) -> None:
    job = queue(client, signup(), "runbook.md", RUNBOOK, db)
    assert claim() == job.id
    assert claim() is None
