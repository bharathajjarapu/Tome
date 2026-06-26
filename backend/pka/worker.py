"""Ingestion worker. Run one with `python -m pka.worker`; several is also safe."""

import logging
import time
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from pka import storage
from pka.core.config import settings
from pka.core.db import SessionLocal
from pka.core.log import setup as setup_logging
from pka.ingestion.nodes import build
from pka.ingestion.parse import ParseError, parse
from pka.models import Document, IngestionJob, Project, State
from pka.rag import store

log = logging.getLogger(__name__)


def process_job(jobid: uuid.UUID) -> None:
    """Fetch, parse, chunk and index one document. Records failure on both rows."""
    with SessionLocal() as db:
        job = db.get(IngestionJob, jobid)
        if job is None:
            return
        doc = db.get(Document, job.document_id)
        if doc is None:
            db.delete(job)
            db.commit()
            return
        job.state = doc.state = State.processing
        db.commit()
        try:
            _ingest(db, doc)
        except Exception as exc:
            _fail(db, job, doc, exc)
            return
        job.state = doc.state = State.indexed
        job.error = doc.error = None
        # Read before the commit: a rollback expires the instance and its row may be gone.
        documentid = doc.id
        try:
            db.commit()
        except StaleDataError:
            # The document was deleted while it was indexing, so that delete could not see
            # these nodes. Drop them here or they outlive the document they came from.
            db.rollback()
            store.forget(documentid)


def _ingest(db: Session, doc: Document) -> None:
    teamid = db.scalars(select(Project.team_id).where(Project.id == doc.project_id)).one()
    text = parse(storage.open(doc.storage_key), doc.filename)
    # A retry must not leave the previous attempt's nodes behind.
    store.forget(doc.id)
    store.add(
        build(
            text,
            team_id=teamid,
            project_id=doc.project_id,
            document_id=doc.id,
            document_name=doc.filename,
        )
    )


def _fail(db: Session, job: IngestionJob, doc: Document, exc: Exception) -> None:
    """Leave no partial chunks behind, then record the failure and decide on a retry."""
    log.exception("ingestion failed for document %s (job %s)", doc.id, job.id)
    store.forget(doc.id)
    # A parse error names the file and nothing internal; anything else stays out of the response.
    message = str(exc) if isinstance(exc, ParseError) else "ingestion failed"
    job.attempts += 1
    job.error = doc.error = message
    # While retries remain the document is still being worked on, so it must not read as failed.
    spent = job.attempts >= settings.max_attempts
    job.state = doc.state = State.failed if spent else State.uploaded
    db.commit()


def claim() -> uuid.UUID | None:
    """Take the oldest queued job. SKIP LOCKED keeps two workers off the same row."""
    with SessionLocal() as db:
        job = db.scalars(
            select(IngestionJob)
            .where(IngestionJob.state == State.uploaded)
            .order_by(IngestionJob.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        ).first()
        if job is None:
            return None
        job.state = State.processing
        db.commit()
        return job.id


def tick() -> bool:
    """One pass of the loop, and the only place failure stops here: a single bad document
    must not take the whole queue down with it. True when a job was picked up."""
    try:
        jobid = claim()
        if jobid is None:
            return False
        process_job(jobid)
        return True
    except Exception:
        log.exception("worker iteration failed")
        return False


def run() -> None:
    setup_logging()
    log.info("worker started")
    while True:
        if not tick():
            time.sleep(settings.poll_seconds)


if __name__ == "__main__":
    run()
