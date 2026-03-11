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
    jwt_secret: SecretStr
    jwt_ttl_minutes: int = 60
    max_upload_bytes: int = 25_000_000
    chunk_size: int = 1200
    chunk_overlap: int = 150
    max_attempts: int = 3
    poll_seconds: float = 2.0
    # Formats the parser handles. Text files are read directly, the rest go through AnyDoc.
    allowed_extensions: set[str] = {
        ".pdf", ".docx", ".doc", ".odt", ".rtf", ".pptx", ".xlsx", ".epub", ".csv", ".md", ".txt",
    }


# Read once at import so a missing variable fails at startup, not at first request.
settings = Settings()
