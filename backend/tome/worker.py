"""Ingestion worker. Run one with `python -m tome.worker`; several is also safe."""

import logging
import time
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from tome import storage
from tome.core.config import settings
from tome.core.db import SessionLocal
from tome.core.log import setup as setup_logging
from tome.ingestion.nodes import build
from tome.ingestion.parse import ParseError, parse
from tome.models import Document, IngestionJob, Project, State
from tome.rag import store

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
        # Read before the commit, so no transaction stays open through parsing and embedding.
        teamid = db.scalars(select(Project.team_id).where(Project.id == doc.project_id)).one()
        job.state = doc.state = State.processing
        db.commit()
        try:
            _ingest(doc, teamid)
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


def _ingest(doc: Document, teamid: uuid.UUID) -> None:
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
    """Take the oldest queued job, or one whose worker died mid-run.
    SKIP LOCKED keeps two workers off the same row."""
    now = datetime.now(UTC)
    abandoned = and_(
        IngestionJob.state == State.processing,
        IngestionJob.claimed_at < now - timedelta(minutes=settings.stale_minutes),
    )
    with SessionLocal() as db:
        job = db.scalars(
            select(IngestionJob)
            .where(or_(IngestionJob.state == State.uploaded, abandoned))
            .order_by(IngestionJob.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        ).first()
        if job is None:
            return None
        if job.state == State.processing:
            # The worker died with it, so that run counts as a failure. A document that
            # crashes the worker every time must stop being retried.
            job.attempts += 1
            if job.attempts >= settings.max_attempts:
                doc = db.get(Document, job.document_id)
                job.state = State.failed
                job.error = "ingestion failed"
                if doc is not None:
                    doc.state, doc.error = State.failed, job.error
                db.commit()
                return None
        job.state = State.processing
        job.claimed_at = now
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
