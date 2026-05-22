import uuid

import pytest

from pka.ingestion.chunk import split
from pka.rag import index

DOC = """# Runbook

Restart the ingestion worker before the database.

## Backups

Backups run nightly and are kept for thirty days.
"""

TEAM, PROJECT = uuid.uuid4(), uuid.uuid4()


def indexdoc(documentid: uuid.UUID, text: str = DOC) -> int:
    chunks = split(
        text,
        team_id=TEAM,
        project_id=PROJECT,
        document_id=documentid,
        document_name="runbook.md",
    )
    return index.index(chunks)


def test_reindexing_replaces_rather_than_appends() -> None:
    documentid = uuid.uuid4()
    first = indexdoc(documentid)
    assert first == index.count(documentid) > 0
    indexdoc(documentid)
    assert index.count(documentid) == first


def test_payload_carries_every_identifier() -> None:
    documentid = uuid.uuid4()
    indexdoc(documentid)
    points, _ = index.client().scroll(
        index.COLLECTION, scroll_filter=index.match("document_id", documentid), limit=1
    )
    payload = points[0].payload
    assert payload["team_id"] == str(TEAM)
    assert payload["project_id"] == str(PROJECT)
    assert payload["document_id"] == str(documentid)
    assert uuid.UUID(payload["chunk_id"])
    assert payload["document_name"] == "runbook.md"
    assert payload["section"]


def test_forget_removes_only_that_document() -> None:
    kept, dropped = uuid.uuid4(), uuid.uuid4()
    indexdoc(kept)
    indexdoc(dropped)
    index.forget(dropped)
    assert index.count(dropped) == 0
    assert index.count(kept) > 0


def test_two_workers_can_create_the_collection_at_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """The loser of the race sees "already exists" and carries on rather than failing a job."""
    index.ensure_collection()
    index.ensure_collection.cache_clear()

    exists = index.client().collection_exists
    seen: list[str] = []

    def stale(name: str) -> bool:
        # The first look happens before the other worker's create lands.
        seen.append(name)
        return exists(name) if len(seen) > 1 else False

    monkeypatch.setattr(index.client(), "collection_exists", stale)
    index.ensure_collection()

    documentid = uuid.uuid4()
    assert indexdoc(documentid) == index.count(documentid) > 0
