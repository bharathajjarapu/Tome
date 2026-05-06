from fastapi import APIRouter

from pka.core.db import Db
from pka.core.deps import AccessibleConversation
from pka.schemas import CitationOut, ConversationOut, MessageOut
from pka.services import chat

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
