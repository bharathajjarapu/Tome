import uuid

from sqlalchemy.orm import Session

from app.models import Conversation, Message, Role


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
