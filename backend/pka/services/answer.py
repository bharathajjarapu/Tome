"""Streams an answer as Server-Sent Events. Frames are built by hand; no SSE dependency."""

import json
import logging
import uuid
from collections.abc import Iterator

from sqlalchemy.orm import Session

from pka.core.db import SessionLocal
from pka.models import Citation, Conversation, Message, Role
from pka.rag import generate, prompts
from pka.rag.context import build
from pka.rag.retrieve import Hit

log = logging.getLogger(__name__)

# How much of a passage is stored and sent with a citation.
SNIPPET = 400


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
    question: str,
    teamid: uuid.UUID,
    projectid: uuid.UUID,
    conversationid: uuid.UUID,
    messageid: uuid.UUID,
) -> Iterator[str]:
    """message_start, then tokens, then one citation per source, then message_end."""
    yield frame("message_start", {"message_id": str(messageid)})
    try:
        context = build(question, teamid, projectid)
        # Nothing relevant was found, so say so instead of paying for a guess.
        tokens = (
            generate.stream(question, context.text)
            if context.enough
            else iter([prompts.REFUSAL])
        )
        answer = ""
        for token in tokens:
            answer += token
            yield frame("token", {"text": token})
        for hit in context.hits:
            yield frame("citation", citation(hit))
        stored = persist(conversationid, answer, context.hits)
        yield frame("message_end", {"message_id": str(stored)})
    except Exception:
        log.exception("streaming failed for message %s", messageid)
        yield frame("error", {"detail": "The answer could not be generated"})


def persist(conversationid: uuid.UUID, answer: str, hits: list[Hit]) -> uuid.UUID:
    """Store the finished answer and one citation row per source."""
    with SessionLocal() as db:
        message = Message(conversation_id=conversationid, role=Role.assistant, content=answer)
        db.add(message)
        db.flush()
        db.add_all(
            Citation(
                message_id=message.id,
                document_id=hit.document_id,
                chunk_id=hit.chunk_id,
                page=hit.page,
                section=hit.section,
                snippet=hit.text[:SNIPPET],
            )
            for hit in hits
        )
        db.commit()
        return message.id


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
