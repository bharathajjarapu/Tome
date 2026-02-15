import hashlib
import uuid

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
