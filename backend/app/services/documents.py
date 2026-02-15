import hashlib
import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import storage
from app.models import Document, IngestionJob, State


def create(db: Session, projectid: uuid.UUID, filename: str, data: bytes) -> Document:
    """Store the file and queue it. Parsing happens in the worker, never here."""
    key = storage.save(data, filename)
    doc = Document(
        project_id=projectid,
        filename=filename,
        storage_key=key,
        sha256=hashlib.sha256(data).hexdigest(),
        state=State.uploaded,
    )
    db.add(doc)
    db.flush()
    db.add(IngestionJob(document_id=doc.id, state=State.uploaded))
    db.commit()
    return doc


def listfor(db: Session, projectid: uuid.UUID) -> Sequence[Document]:
    return db.scalars(
        select(Document)
        .where(Document.project_id == projectid)
        .order_by(Document.created_at)
    ).all()


def delete(db: Session, doc: Document) -> None:
    """Remove the file and the rows. Chunks go too, once the index module exists (ticket 13)."""
    storage.delete(doc.storage_key)
    db.delete(doc)
    db.commit()
