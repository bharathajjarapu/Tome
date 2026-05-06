import pytest
from pydantic import ValidationError

from pka.core.config import Settings


def env(**overrides: str) -> dict[str, str]:
    base = {
        "database_url": "postgresql+psycopg://u:p@localhost/db",
        "qdrant_url": "http://localhost:6333",
        "upload_dir": "./data/uploads",
        "llm_api_key": "topsecretvalue",
        "llm_model": "some-model",
    }
    return base | overrides


def test_loads_from_env() -> None:
    s = Settings(_env_file=None, **env())
    assert s.qdrant_url == "http://localhost:6333"
    assert s.llm_api_key.get_secret_value() == "topsecretvalue"
    assert "topsecretvalue" not in repr(s)


def test_missing_field_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    values = env()
    del values["database_url"]
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **values)
