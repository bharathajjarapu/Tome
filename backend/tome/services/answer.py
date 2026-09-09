"""Streams an answer as Server-Sent Events. Frames are built by hand; no SSE dependency."""

import json
import logging
import uuid
from collections.abc import Iterator
from itertools import takewhile

from llama_index.core.base.llms.types import ChatMessage
from llama_index.core.schema import NodeWithScore
from sqlalchemy import select
from sqlalchemy.orm import Session

from tome.core.db import SessionLocal
from tome.models import Citation, Conversation, Message, Role
from tome.rag.chat import engine
from tome.services import chat

log = logging.getLogger(__name__)

# How much of a passage is stored and sent with a citation.
SNIPPET = 400


def find(
    db: Session, projectid: uuid.UUID, userid: uuid.UUID, messageid: uuid.UUID
) -> Message | None:
    """The question to answer, or None when it is not this user's to see."""
    message = db.get(Message, messageid)
    if message is None or message.role != Role.user:
        return None
    conversation = db.get(Conversation, message.conversation_id)
    if conversation is None:
        return None
    if conversation.project_id != projectid or conversation.user_id != userid:
        return None
    return message


def answered(db: Session, question: Message) -> bool:
    """True when the next message in the thread is already this question's answer."""
    after = db.scalars(
        select(Message.role)
        .where(
            Message.conversation_id == question.conversation_id,
            Message.created_at > question.created_at,
        )
        .order_by(Message.created_at, Message.id)
        .limit(1)
    ).first()
    return after == Role.assistant


def history(db: Session, conversationid: uuid.UUID, messageid: uuid.UUID) -> list[ChatMessage]:
    """Everything said before this question, in the shape the chat engine wants."""
    before = takewhile(lambda row: row[0].id != messageid, chat.history(db, conversationid))
    return [ChatMessage(role=message.role.value, content=message.content) for message, _ in before]


def events(
    question: str,
    teamid: uuid.UUID,
    projectid: uuid.UUID,
    conversationid: uuid.UUID,
    messageid: uuid.UUID,
    thread: list[ChatMessage],
) -> Iterator[str]:
    """message_start, then tokens, then one citation per source, then message_end."""
    yield frame("message_start", {"message_id": str(messageid)})
    try:
        response = engine(teamid, projectid, thread).stream_chat(question)
        answer = ""
        for token in response.response_gen:
            answer += token
            yield frame("token", {"text": token})
        # Retrieval already happened, so the sources are known before the first token.
        sources = response.source_nodes
        for node in sources:
            yield frame("citation", citation(node))
        stored = persist(conversationid, answer, sources)
        yield frame("message_end", {"message_id": str(stored)})
    except Exception:
        log.exception("streaming failed for message %s", messageid)
        yield frame("error", {"detail": "The answer could not be generated"})


def persist(conversationid: uuid.UUID, answer: str, sources: list[NodeWithScore]) -> uuid.UUID:
    """Store the finished answer and one citation row per source."""
    with SessionLocal() as db:
        message = Message(conversation_id=conversationid, role=Role.assistant, content=answer)
        db.add(message)
        db.flush()
        db.add_all(
            Citation(
                message_id=message.id,
                document_id=uuid.UUID(str(node.node.ref_doc_id)),
                chunk_id=node.node.node_id,
                page=node.node.metadata.get("page"),
                section=node.node.metadata.get("section"),
                snippet=node.node.get_content()[:SNIPPET],
            )
            for node in sources
        )
        db.commit()
        return message.id


def frame(event: str, data: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def citation(node: NodeWithScore) -> dict[str, object]:
    return {
        "document_id": str(node.node.ref_doc_id),
        "document_name": node.node.metadata.get("document_name"),
        "chunk_id": node.node.node_id,
        "section": node.node.metadata.get("section"),
        "page": node.node.metadata.get("page"),
        "snippet": node.node.get_content()[:SNIPPET],
    }
