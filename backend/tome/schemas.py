import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from tome.core.security import MAX_PASSWORD_BYTES
from tome.models import Role, State


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=MAX_PASSWORD_BYTES)

    @field_validator("email")
    @classmethod
    def lower(cls, email: str) -> str:
        return email.lower()


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ProjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    team_id: uuid.UUID


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    state: State
    error: str | None = None
    created_at: datetime


class ChatIn(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    conversation_id: uuid.UUID | None = None


class ChatOut(BaseModel):
    conversation_id: uuid.UUID
    message_id: uuid.UUID


class CitationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_id: uuid.UUID
    chunk_id: str
    page: int | None = None
    section: str | None = None
    snippet: str


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: Role
    content: str
    citations: list[CitationOut] = []


class ConversationSummary(BaseModel):
    """One row of the history sidebar: the conversation and the question that opened it."""

    id: uuid.UUID
    title: str
    created_at: datetime


class ConversationOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    messages: list[MessageOut]
