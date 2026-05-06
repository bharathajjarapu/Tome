from pathlib import Path

from pka import storage
from pka.core.config import settings


def test_round_trip() -> None:
    key = storage.save(b"hello", "notes.pdf")
    assert key.endswith(".pdf")
    assert storage.open(key) == b"hello"
    storage.delete(key)
    assert not storage.path(key).exists()


def test_traversal_stays_inside_upload_dir() -> None:
    key = storage.save(b"x", "../../etc/passwd")
    stored = storage.path(key).resolve()
    assert stored.parent == Path(settings.upload_dir).resolve()
    assert "passwd" not in key
