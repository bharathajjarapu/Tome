"""Authentication and authorisation dependencies. No route reads a token itself."""

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, Path, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.db import Db
from app.core.security import read_token
from app.models import Document, Membership, Project, User

bearer = HTTPBearer(auto_error=False)

UNAUTHORISED = HTTPException(
    status.HTTP_401_UNAUTHORIZED,
    "Not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


def current_user(
    db: Db,
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> User:
    if creds is None:
        raise UNAUTHORISED
    userid = read_token(creds.credentials)
    if userid is None:
        raise UNAUTHORISED
    user = db.get(User, userid)
    if user is None:
        raise UNAUTHORISED
    return user


CurrentUser = Annotated[User, Depends(current_user)]


def project_access(
    db: Db,
    user: CurrentUser,
    project_id: Annotated[uuid.UUID, Path()],
) -> Project:
    """Load a project the caller's teams own. 404 rather than 403, so nothing leaks."""
    project = db.get(Project, project_id)
    if project is not None:
        member = db.query(Membership).filter_by(user_id=user.id, team_id=project.team_id).first()
        if member is not None:
            return project
    raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")


AccessibleProject = Annotated[Project, Depends(project_access)]


def document_access(
    db: Db,
    user: CurrentUser,
    document_id: Annotated[uuid.UUID, Path()],
) -> Document:
    """Same rule as project_access, one level down."""
    doc = db.get(Document, document_id)
    if doc is not None:
        project = db.get(Project, doc.project_id)
        if project is not None:
            member = db.query(Membership).filter_by(
                user_id=user.id, team_id=project.team_id
            ).first()
            if member is not None:
                return doc
    raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")


AccessibleDocument = Annotated[Document, Depends(document_access)]
