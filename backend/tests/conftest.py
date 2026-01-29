import os
import pathlib
import tempfile

# Set before any app import: settings are read at import time.
# Point TEST_DATABASE_URL at a Postgres instance to run the same suite against it.
_tmpdb = os.path.join(tempfile.mkdtemp(prefix="pka-test-"), "test.db")
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", f"sqlite+pysqlite:///{_tmpdb}")
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")
os.environ.setdefault("UPLOAD_DIR", tempfile.mkdtemp(prefix="pka-uploads-"))
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_MODEL", "test-model")

from collections.abc import Iterator  # noqa: E402

import pytest  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from alembic import command  # noqa: E402
from app.core.db import SessionLocal, engine  # noqa: E402
from app.models import Base  # noqa: E402

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


@pytest.fixture
def db() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session


@pytest.fixture
def client() -> TestClient:
    from app.main import app

    return TestClient(app)
