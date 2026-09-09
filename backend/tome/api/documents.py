from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, status

from tome.core.config import settings
from tome.core.db import Db
from tome.core.deps import AccessibleDocument, AccessibleProject
from tome.schemas import DocumentOut
from tome.services import documents

router = APIRouter(tags=["documents"])


@router.post(
    "/projects/{project_id}/documents",
    response_model=DocumentOut,
    status_code=status.HTTP_201_CREATED,
)
def upload(project: AccessibleProject, db: Db, file: UploadFile) -> DocumentOut:
    filename = file.filename or ""
    if Path(filename).suffix.lower() not in settings.allowed_extensions:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Unsupported file type"
        )
    if file.size is not None and file.size > settings.max_upload_bytes:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "File is too large")

    data = file.file.read(settings.max_upload_bytes + 1)
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "File is too large")

    doc = documents.create(db, project.id, filename, data)
    return DocumentOut.model_validate(doc)


@router.get("/projects/{project_id}/documents", response_model=list[DocumentOut])
def index(project: AccessibleProject, db: Db) -> list[DocumentOut]:
    return [DocumentOut.model_validate(d) for d in documents.listfor(db, project.id)]


@router.get("/documents/{document_id}/status", response_model=DocumentOut)
def read_status(doc: AccessibleDocument) -> DocumentOut:
    return DocumentOut.model_validate(doc)


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove(doc: AccessibleDocument, db: Db) -> None:
    documents.delete(db, doc)
