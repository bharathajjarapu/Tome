"""The one call site for the LLM. Swap the provider here."""

import json
from collections.abc import Iterator

import httpx

from pka.core.config import settings
from pka.rag import prompts


def stream(question: str, context: str) -> Iterator[str]:
    """Yield the answer token by token from an OpenAI-compatible endpoint."""
    body = {
        "model": settings.llm_model,
        "stream": True,
        "messages": [
            {"role": "system", "content": prompts.SYSTEM},
            {"role": "user", "content": prompts.question(question, context)},
        ],
    }
    headers = {"Authorization": f"Bearer {settings.llm_api_key.get_secret_value()}"}
    with httpx.stream(
        "POST",
        f"{settings.llm_base_url}/chat/completions",
        json=body,
        headers=headers,
        timeout=settings.llm_timeout,
    ) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if not line.startswith("data: "):
                continue
            payload = line.removeprefix("data: ")
            if payload == "[DONE]":
                return
            token = json.loads(payload)["choices"][0]["delta"].get("content")
            if token:
                yield token
