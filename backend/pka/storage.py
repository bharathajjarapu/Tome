"""Uploaded files on the local filesystem. Swap this module to store them elsewhere."""

import re
import uuid
from pathlib import Path

from pka.core.config import settings

SUFFIX = re.compile(r"^\.[A-Za-z0-9]{1,10}$")


def path(key: str) -> Path:
    return settings.upload_dir / key


def save(data: bytes, filename: str) -> str:
    """Store the bytes under a generated key. The uploaded name never reaches the path."""
    suffix = Path(filename).suffix.lower()
    key = uuid.uuid4().hex + (suffix if SUFFIX.match(suffix) else "")
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    path(key).write_bytes(data)
    return key


def open(key: str) -> bytes:
    return path(key).read_bytes()


def delete(key: str) -> None:
    path(key).unlink(missing_ok=True)
