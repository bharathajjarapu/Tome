import uuid
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from tome.models import Citation, Conversation, Message, Role


def ask(
    db: Session,
    projectid: uuid.UUID,
    userid: uuid.UUID,
    question: str,
    conversationid: uuid.UUID | None,
) -> Message:
    """Persist the question, starting a conversation if this is the first one."""
    conversation = _conversation(db, projectid, userid, conversationid)
    message = Message(conversation_id=conversation.id, role=Role.user, content=question)
    db.add(message)
    db.commit()
    return message


def _conversation(
    db: Session, projectid: uuid.UUID, userid: uuid.UUID, conversationid: uuid.UUID | None
) -> Conversation:
    if conversationid is not None:
        existing = db.get(Conversation, conversationid)
        # A conversation from another project or another user is treated as absent.
        if existing is not None and existing.project_id == projectid and existing.user_id == userid:
            return existing
    conversation = Conversation(project_id=projectid, user_id=userid)
    db.add(conversation)
    db.flush()
    return conversation


def history(db: Session, conversationid: uuid.UUID) -> list[tuple[Message, list[Citation]]]:
    """Messages oldest first, each with its citations. Two queries, whatever the length."""
    messages = db.scalars(
        select(Message)
        .where(Message.conversation_id == conversationid)
        .order_by(Message.created_at, Message.id)
    ).all()
    cited: dict[uuid.UUID, list[Citation]] = defaultdict(list)
    for citation in db.scalars(
        select(Citation).where(Citation.message_id.in_([m.id for m in messages]))
    ):
        cited[citation.message_id].append(citation)
    return [(message, cited[message.id]) for message in messages]


def listfor(
    db: Session, projectid: uuid.UUID, userid: uuid.UUID
) -> list[tuple[Conversation, str]]:
    """The caller's conversations in this project, newest first, each with its opening question.
    One query that reads one message per conversation, however long the threads are."""
    opening = (
        select(Message.content)
        .where(Message.conversation_id == Conversation.id, Message.role == Role.user)
        .order_by(Message.created_at, Message.id)
        .limit(1)
        .correlate(Conversation)
        .scalar_subquery()
    )
    rows = db.execute(
        select(Conversation, opening)
        .where(Conversation.project_id == projectid, Conversation.user_id == userid)
        .order_by(Conversation.created_at.desc())
    ).all()
    return [(conversation, question) for conversation, question in rows if question is not None]
