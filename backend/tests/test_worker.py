import uuid
from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from llama_index.core.schema import BaseNode
from sqlalchemy import select
from sqlalchemy.orm import Session

from pka import worker
from pka.core.config import settings
from pka.core.db import SessionLocal
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
    """A retry is still in progress, so the document reads as pending rather than failed."""
    job = queue(client, signup(), "broken.pdf", b"%PDF-1.4 not a pdf", db)
    process_job(job.id)

    db.expunge_all()
    doc = db.get(Document, job.document_id)
    assert doc.state == State.uploaded
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
    assert db.get(Document, job.document_id).state == State.failed


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


def abandon(jobid: uuid.UUID) -> None:
    """Leave the job as a worker that died mid-run would: processing, claimed long ago."""
    with SessionLocal() as session:
        job = session.get(IngestionJob, jobid)
        assert job is not None
        job.claimed_at = datetime.now(UTC) - timedelta(minutes=settings.stale_minutes + 1)
        session.commit()


def test_a_job_whose_worker_died_is_taken_again(
    client: TestClient, signup: Callable[..., Account], db: Session
) -> None:
    job = queue(client, signup(), "runbook.md", RUNBOOK, db)
    assert claim() == job.id
    abandon(job.id)

    assert claim() == job.id
    db.expire_all()
    assert db.get(IngestionJob, job.id).attempts == 1


def test_a_job_that_keeps_killing_its_worker_is_failed(
    client: TestClient, signup: Callable[..., Account], db: Session
) -> None:
    job = queue(client, signup(), "runbook.md", RUNBOOK, db)
    for _ in range(settings.max_attempts):
        claim()
        abandon(job.id)
    assert claim() is None

    db.expire_all()
    assert db.get(IngestionJob, job.id).state == State.failed
    assert db.get(Document, job.document_id).state == State.failed


def test_a_document_deleted_while_it_indexes_leaves_no_nodes(
    client: TestClient,
    signup: Callable[..., Account],
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The delete cannot see nodes written after it ran, so the worker cleans up its own."""
    job = queue(client, signup(), "runbook.md", RUNBOOK, db)
    documentid = job.document_id
    added = store.add

    def add_then_delete(nodes: Sequence[BaseNode]) -> int:
        count = added(nodes)
        with SessionLocal() as other:
            other.delete(other.get(Document, documentid))
            other.commit()
        return count

    monkeypatch.setattr(worker.store, "add", add_then_delete)
    process_job(job.id)

    assert store.count(documentid) == 0


def test_one_bad_job_does_not_stop_the_worker(
    client: TestClient, signup: Callable[..., Account], db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A crash on one document must not take the queue down with it."""
    queue(client, signup(), "runbook.md", RUNBOOK, db)

    def boom(jobid: uuid.UUID) -> None:
        raise RuntimeError("kaboom")

    monkeypatch.setattr(worker, "process_job", boom)
    assert worker.tick() is False
