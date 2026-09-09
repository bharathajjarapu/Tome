"""Authentication and authorisation dependencies. No route reads a token itself."""

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, Path, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from tome.core.db import Db
from tome.core.security import read_token
from tome.models import Conversation, Document, Membership, Project, User

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


def member_of(db: Session, user: User, teamid: uuid.UUID) -> bool:
    """The one membership check. Everything below is built on it."""
    return db.query(Membership).filter_by(user_id=user.id, team_id=teamid).first() is not None


def _in_project(db: Session, user: User, projectid: uuid.UUID) -> bool:
    project = db.get(Project, projectid)
    return project is not None and member_of(db, user, project.team_id)


def _missing(what: str) -> HTTPException:
    """404 rather than 403 everywhere, so a wrong guess leaks nothing."""
    return HTTPException(status.HTTP_404_NOT_FOUND, f"{what} not found")


def project_access(
    db: Db,
    user: CurrentUser,
    project_id: Annotated[uuid.UUID, Path()],
) -> Project:
    project = db.get(Project, project_id)
    if project is None or not member_of(db, user, project.team_id):
        raise _missing("Project")
    return project


AccessibleProject = Annotated[Project, Depends(project_access)]


def document_access(
    db: Db,
    user: CurrentUser,
    document_id: Annotated[uuid.UUID, Path()],
) -> Document:
    doc = db.get(Document, document_id)
    if doc is None or not _in_project(db, user, doc.project_id):
        raise _missing("Document")
    return doc


AccessibleDocument = Annotated[Document, Depends(document_access)]


def conversation_access(
    db: Db,
    user: CurrentUser,
    conversation_id: Annotated[uuid.UUID, Path()],
) -> Conversation:
    conversation = db.get(Conversation, conversation_id)
    if conversation is None or not _in_project(db, user, conversation.project_id):
        raise _missing("Conversation")
    return conversation


AccessibleConversation = Annotated[Conversation, Depends(conversation_access)]
