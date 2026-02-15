from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, status

from app.core.config import settings
from app.core.db import Db
from app.core.deps import AccessibleProject
from app.schemas import DocumentOut
from app.services import documents

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
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File is too large")

    data = file.file.read(settings.max_upload_bytes + 1)
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File is too large")

    doc = documents.create(db, project.id, filename, data)
    return DocumentOut.model_validate(doc)
