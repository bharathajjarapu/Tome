"""Database tables. PostgreSQL is the source of truth; the vector store never is."""

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class State(StrEnum):
    uploaded = "uploaded"
    processing = "processing"
    indexed = "indexed"
    failed = "failed"


class Role(StrEnum):
    user = "user"
    assistant = "assistant"


class Base(DeclarativeBase):
    pass


def pk() -> Mapped[uuid.UUID]:
    return mapped_column(primary_key=True, default=uuid.uuid4)


def fk(target: str) -> Mapped[uuid.UUID]:
    return mapped_column(ForeignKey(target, ondelete="CASCADE"), index=True)


def created() -> Mapped[datetime]:
    # Set here rather than by the database: SQLite's now() only has second resolution,
    # which is not enough to order two rows written in the same request.
    return mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )


# native_enum=False keeps this a VARCHAR + CHECK, so the same DDL runs on Postgres and SQLite.
def state_col() -> Mapped[State]:
    return mapped_column(Enum(State, native_enum=False, length=16), default=State.uploaded)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = pk()
    email: Mapped[str] = mapped_column(String(320), unique=True)
    password_hash: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = created()


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[uuid.UUID] = pk()
    name: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = created()


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("user_id", "team_id"),)

    id: Mapped[uuid.UUID] = pk()
    user_id: Mapped[uuid.UUID] = fk("users.id")
    team_id: Mapped[uuid.UUID] = fk("teams.id")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = pk()
    team_id: Mapped[uuid.UUID] = fk("teams.id")
    name: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = created()


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = pk()
    project_id: Mapped[uuid.UUID] = fk("projects.id")
    filename: Mapped[str] = mapped_column(String(500))
    storage_key: Mapped[str] = mapped_column(String(200))
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    state: Mapped[State] = state_col()
    error: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = created()


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    id: Mapped[uuid.UUID] = pk()
    document_id: Mapped[uuid.UUID] = fk("documents.id")
    state: Mapped[State] = state_col()
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = created()


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = pk()
    project_id: Mapped[uuid.UUID] = fk("projects.id")
    user_id: Mapped[uuid.UUID] = fk("users.id")
    created_at: Mapped[datetime] = created()


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = pk()
    conversation_id: Mapped[uuid.UUID] = fk("conversations.id")
    role: Mapped[Role] = mapped_column(Enum(Role, native_enum=False, length=16))
    content: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = created()


class Citation(Base):
    __tablename__ = "citations"

    id: Mapped[uuid.UUID] = pk()
    message_id: Mapped[uuid.UUID] = fk("messages.id")
    document_id: Mapped[uuid.UUID] = fk("documents.id")
    chunk_id: Mapped[str] = mapped_column(String(100))
    page: Mapped[int | None] = mapped_column(Integer, default=None)
    section: Mapped[str | None] = mapped_column(String(500), default=None)
    snippet: Mapped[str] = mapped_column(Text)
