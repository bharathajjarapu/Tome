"""Ingestion worker. Run one with `python -m pka.worker`; several is also safe."""

import logging
import time
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from pka import storage
from pka.core.config import settings
from pka.core.db import SessionLocal
from pka.core.log import setup as setup_logging
from pka.ingestion.chunk import split
from pka.ingestion.parse import ParseError, parse
from pka.models import Document, IngestionJob, Project, State
from pka.rag import index

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
        db.commit()


def _ingest(db: Session, doc: Document) -> None:
    teamid = db.scalars(select(Project.team_id).where(Project.id == doc.project_id)).one()
    text = parse(storage.open(doc.storage_key), doc.filename)
    index.index(
        split(
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
    index.forget(doc.id)
    # A parse error names the file and nothing internal; anything else stays out of the response.
    message = str(exc) if isinstance(exc, ParseError) else "ingestion failed"
    job.attempts += 1
    job.error = doc.error = message
    job.state = State.uploaded if job.attempts < settings.max_attempts else State.failed
    doc.state = State.failed
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


def run() -> None:
    setup_logging()
    log.info("worker started")
    while True:
        jobid = claim()
        if jobid is None:
            time.sleep(settings.poll_seconds)
            continue
        process_job(jobid)


if __name__ == "__main__":
    run()
