import uuid

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from pka.core.db import Db
from pka.core.deps import AccessibleProject, CurrentUser
from pka.schemas import ChatIn, ChatOut, ConversationSummary
from pka.services import answer, chat

router = APIRouter(prefix="/projects", tags=["chat"])


@router.post("/{project_id}/chat", response_model=ChatOut, status_code=status.HTTP_201_CREATED)
def ask(project: AccessibleProject, user: CurrentUser, db: Db, body: ChatIn) -> ChatOut:
    """Store the question. The answer is streamed by a separate GET."""
    message = chat.ask(db, project.id, user.id, body.question, body.conversation_id)
    return ChatOut(conversation_id=message.conversation_id, message_id=message.id)


@router.get("/{project_id}/chat/stream")
def stream(
    project: AccessibleProject, user: CurrentUser, db: Db, message_id: uuid.UUID
) -> StreamingResponse:
    """Answer a stored question, streaming the tokens as they arrive."""
    message = answer.find(db, project.id, user.id, message_id)
    if message is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Message not found")
    return StreamingResponse(
        answer.events(
            message.content, project.team_id, project.id, message.conversation_id, message.id
        ),
        media_type="text/event-stream",
    )


@router.get("/{project_id}/conversations", response_model=list[ConversationSummary])
def conversations(
    project: AccessibleProject, user: CurrentUser, db: Db
) -> list[ConversationSummary]:
    """The caller's past conversations in this project, newest first."""
    return [
        ConversationSummary(id=conversation.id, title=question, created_at=conversation.created_at)
        for conversation, question in chat.listfor(db, project.id, user.id)
    ]
