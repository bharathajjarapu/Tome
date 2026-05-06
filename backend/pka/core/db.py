import sqlite3
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from pka.core.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(engine, expire_on_commit=False)


@event.listens_for(Engine, "connect")
def enable_sqlite_foreign_keys(conn: object, _record: object) -> None:
    """SQLite ignores foreign keys unless asked. Postgres always enforces them."""
    if isinstance(conn, sqlite3.Connection):
        conn.execute("PRAGMA foreign_keys=ON")


def get_db() -> Iterator[Session]:
    with SessionLocal() as db:
        yield db


Db = Annotated[Session, Depends(get_db)]
