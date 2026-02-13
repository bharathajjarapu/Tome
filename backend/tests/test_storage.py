from pathlib import Path

import pytest

from app import storage
from app.core.config import settings


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


def test_open_unknown_key_raises() -> None:
    with pytest.raises(FileNotFoundError):
        storage.open("does-not-exist")


def test_delete_is_idempotent() -> None:
    key = storage.save(b"x", "a.txt")
    storage.delete(key)
    storage.delete(key)
