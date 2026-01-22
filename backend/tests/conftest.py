import os
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
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.db import SessionLocal, engine  # noqa: E402
from app.models import Base  # noqa: E402


@pytest.fixture(autouse=True)
def freshdb() -> Iterator[None]:
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def db() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session


@pytest.fixture
def client() -> TestClient:
    from app.main import app

    return TestClient(app)
