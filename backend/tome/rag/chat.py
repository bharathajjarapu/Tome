"""The chat engine. One per request, scoped to the caller's project and carrying the thread."""

import uuid

from llama_index.core.base.llms.types import ChatMessage
from llama_index.core.chat_engine import CondensePlusContextChatEngine

from tome.rag import prompts, store
from tome.rag.llm import llm
from tome.rag.rerank import Reranker


def engine(
    team_id: uuid.UUID, project_id: uuid.UUID, history: list[ChatMessage]
) -> CondensePlusContextChatEngine:
    """Retrieve, rerank, then answer with the conversation in view.

    `condense_plus_context` rewrites a follow-up into a standalone retrieval query using the
    history, and puts the passages in the system prompt, so an ordinary conversational turn is
    answered instead of being run through retrieval and refused. It skips the rewrite when the
    history is empty, so a first question costs one model call, not two.
    """
    return CondensePlusContextChatEngine.from_defaults(
        retriever=store.retriever(team_id, project_id),
        llm=llm(),
        node_postprocessors=[Reranker()],
        system_prompt=prompts.SYSTEM,
        context_prompt=prompts.CONTEXT,
        chat_history=history,
    )
