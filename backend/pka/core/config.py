from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Every value comes from the environment. Nothing here has a default."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    qdrant_url: str
    upload_dir: Path
    llm_api_key: SecretStr
    llm_model: str
    llm_base_url: str = "https://api.experientiallabs.ai/v1"
    llm_timeout: float = 60.0
    jwt_secret: SecretStr
    jwt_ttl_minutes: int = 60
    max_upload_bytes: int = 25_000_000
    # Tokens per chunk. The embedding model reads 512 of its own tokens and silently drops
    # the rest, so a chunk that does not fit is half-indexed: measured on real documents its
    # tokenizer runs up to 1.2x this count, which is what leaves the headroom here.
    chunk_size: int = 380
    chunk_overlap: int = 50
    max_attempts: int = 3
    poll_seconds: float = 0.5
    # Retrieval: fetch this many candidates, keep this many after reranking.
    top_k: int = 30
    rerank_top_n: int = 6
    # Passages pushed through the reranker at once. Batches are padded to their longest
    # passage, so on a small CPU one at a time is measurably faster than a full batch.
    # This is the reranker's batch only: the vector store keeps its own, much larger one.
    rerank_batch: int = 1

    # Formats the parser handles. Text files are read directly, the rest go through AnyDoc.
    allowed_extensions: set[str] = {
        ".pdf", ".docx", ".doc", ".odt", ".rtf", ".pptx", ".xlsx", ".epub", ".csv",
        ".md", ".markdown", ".txt",
    }


# Read once at import so a missing variable fails at startup, not at first request.
settings = Settings()
