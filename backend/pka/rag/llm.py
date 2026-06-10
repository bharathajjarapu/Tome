"""The one call site for the LLM. Swap the provider here."""

from functools import cache

from llama_index.llms.openai_like import OpenAILike

from pka.core.config import settings


@cache
def llm() -> OpenAILike:
    """Any OpenAI-compatible chat endpoint. `is_chat_model` keeps it off /completions."""
    return OpenAILike(
        model=settings.llm_model,
        api_base=settings.llm_base_url,
        api_key=settings.llm_api_key.get_secret_value(),
        timeout=settings.llm_timeout,
        is_chat_model=True,
    )
