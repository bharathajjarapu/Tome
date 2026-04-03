from fastapi import APIRouter, status

from app.core.db import Db
from app.core.deps import AccessibleProject, CurrentUser
from app.schemas import ChatIn, ChatOut
from app.services import chat

router = APIRouter(prefix="/projects", tags=["chat"])


@router.post("/{project_id}/chat", response_model=ChatOut, status_code=status.HTTP_201_CREATED)
def ask(project: AccessibleProject, user: CurrentUser, db: Db, body: ChatIn) -> ChatOut:
    """Store the question. The answer is streamed by a separate GET."""
    message = chat.ask(db, project.id, user.id, body.question, body.conversation_id)
    return ChatOut(conversation_id=message.conversation_id, message_id=message.id)
