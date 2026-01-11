import os

# Set before any app import: settings are read at import time.
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")
os.environ.setdefault("UPLOAD_DIR", "./data/test-uploads")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_MODEL", "test-model")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    from app.main import app

    return TestClient(app)
