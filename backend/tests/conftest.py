import os
import pathlib
import tempfile

# Set before any app import: settings are read at import time.
# Point TEST_DATABASE_URL at a Postgres instance to run the same suite against it.
_tmpdb = os.path.join(tempfile.mkdtemp(prefix="tome-test-"), "test.db")
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", f"sqlite+pysqlite:///{_tmpdb}")
# Local Qdrant, in process. Point TEST_QDRANT_URL at a server to run against one.
os.environ["QDRANT_URL"] = os.environ.get("TEST_QDRANT_URL", ":memory:")
os.environ.setdefault("UPLOAD_DIR", tempfile.mkdtemp(prefix="tome-uploads-"))
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_MODEL", "test-model")
os.environ.setdefault("LLM_BASE_URL", "http://llm.test/v1")
# At least 32 bytes: a shorter HMAC key is below what SHA256 wants (RFC 7518 3.2).
os.environ.setdefault("JWT_SECRET", "test-secret-long-enough-for-sha256")

from collections.abc import Callable, Iterator  # noqa: E402
from dataclasses import dataclass  # noqa: E402

import pytest  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from llama_index.core.base.llms.types import (  # noqa: E402
    CompletionResponse,
    CompletionResponseGen,
    LLMMetadata,
)
from llama_index.core.llms.callbacks import llm_completion_callback  # noqa: E402
from llama_index.core.llms.custom import CustomLLM  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from alembic import command  # noqa: E402
from tome.core.db import SessionLocal, engine  # noqa: E402
from tome.models import Base, Membership, Project, Team, User  # noqa: E402
from tome.rag import chat as ragchat  # noqa: E402
from tome.rag import store  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session", autouse=True)
def schema() -> Iterator[None]:
    """Build the schema from the migrations, so every run exercises them."""
    cfg = Config(ROOT / "alembic.ini")
    command.upgrade(cfg, "head")
    yield
    command.downgrade(cfg, "base")


@pytest.fixture(autouse=True)
def cleandb(schema: None) -> Iterator[None]:
    yield
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
    # Chunks live outside the database, so they need clearing too.
    store.client().delete_collection(store.COLLECTION)
    store.store.cache_clear()
    store.index.cache_clear()


@pytest.fixture
def db() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session


@pytest.fixture
def client() -> TestClient:
    from tome.main import app

    return TestClient(app)


@dataclass
class Account:
    user: User
    team: Team
    headers: dict[str, str]


@pytest.fixture
def signup(client: TestClient, db: Session) -> Callable[..., Account]:
    """Register a user, log in, and hand back their team plus auth headers."""

    def make(email: str = "sam@example.com", password: str = "correct-horse") -> Account:
        creds = {"email": email, "password": password}
        assert client.post("/auth/register", json=creds).status_code == 201
        token = client.post("/auth/login", json=creds).json()["access_token"]
        user = db.scalars(select(User).where(User.email == email)).one()
        team = db.scalars(
            select(Team).join(Membership, Membership.team_id == Team.id).where(
                Membership.user_id == user.id
            )
        ).one()
        return Account(user, team, {"Authorization": f"Bearer {token}"})

    return make


@pytest.fixture
def newproject(db: Session) -> Callable[..., Project]:
    def make(team: Team, name: str = "Docs") -> Project:
        project = Project(team_id=team.id, name=name)
        db.add(project)
        db.commit()
        return project

    return make


ANSWER = ["Archived ", "logs ", "are ", "kept ", "for ", "ninety ", "days."]


# Module level, because pydantic copies a field default and the recorder must be shared.
ASKED: list[str] = []


class FakeLLM(CustomLLM):
    """Fixed tokens, and a record of every prompt the pipeline built."""

    @property
    def metadata(self) -> LLMMetadata:
        return LLMMetadata(model_name="fake", num_output=64, context_window=4096)

    @llm_completion_callback()
    def complete(
        self, prompt: str, formatted: bool = False, **kwargs: object
    ) -> CompletionResponse:
        ASKED.append(prompt)
        return CompletionResponse(text="".join(ANSWER))

    @llm_completion_callback()
    def stream_complete(
        self, prompt: str, formatted: bool = False, **kwargs: object
    ) -> CompletionResponseGen:
        ASKED.append(prompt)
        text = ""
        for token in ANSWER:
            text += token
            yield CompletionResponse(text=text, delta=token)


@pytest.fixture
def fakellm(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Replace the LLM. The list holds every prompt it was given."""
    ASKED.clear()
    monkeypatch.setattr(ragchat, "llm", FakeLLM)
    return ASKED
