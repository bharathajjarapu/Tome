from fastapi import APIRouter

from app.core.db import Db
from app.core.deps import AccessibleConversation
from app.schemas import CitationOut, ConversationOut, MessageOut
from app.services import chat

router = APIRouter(prefix="/conversations", tags=["chat"])


@router.get("/{conversation_id}", response_model=ConversationOut)
def read(conversation: AccessibleConversation, db: Db) -> ConversationOut:
    return ConversationOut(
        id=conversation.id,
        project_id=conversation.project_id,
        messages=[
            MessageOut(
                id=message.id,
                role=message.role,
                content=message.content,
                citations=[CitationOut.model_validate(c) for c in cited],
            )
            for message, cited in chat.history(db, conversation.id)
        ],
    )
