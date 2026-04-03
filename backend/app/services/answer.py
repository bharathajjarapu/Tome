"""Streams an answer as Server-Sent Events. Frames are built by hand; no SSE dependency."""

import json
import logging
import uuid
from collections.abc import Iterator

from sqlalchemy.orm import Session

from app.models import Conversation, Message
from app.rag import generate
from app.rag.context import build
from app.rag.retrieve import Hit

log = logging.getLogger(__name__)


def find(
    db: Session, projectid: uuid.UUID, userid: uuid.UUID, messageid: uuid.UUID
) -> Message | None:
    """The question to answer, or None when it is not this user's to see."""
    message = db.get(Message, messageid)
    if message is None:
        return None
    conversation = db.get(Conversation, message.conversation_id)
    if conversation is None:
        return None
    if conversation.project_id != projectid or conversation.user_id != userid:
        return None
    return message


def events(
    question: str, teamid: uuid.UUID, projectid: uuid.UUID, messageid: uuid.UUID
) -> Iterator[str]:
    """message_start, then tokens, then one citation per source, then message_end."""
    yield frame("message_start", {"message_id": str(messageid)})
    try:
        context = build(question, teamid, projectid)
        for token in generate.stream(question, context.text):
            yield frame("token", {"text": token})
        for hit in context.hits:
            yield frame("citation", citation(hit))
        yield frame("message_end", {"message_id": str(messageid)})
    except Exception:
        log.exception("streaming failed for message %s", messageid)
        yield frame("error", {"detail": "The answer could not be generated"})


def frame(event: str, data: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def citation(hit: Hit) -> dict[str, object]:
    return {
        "document_id": str(hit.document_id),
        "document_name": hit.document_name,
        "chunk_id": hit.chunk_id,
        "section": hit.section,
        "page": hit.page,
        "snippet": hit.text[:SNIPPET],
    }


SNIPPET = 400
