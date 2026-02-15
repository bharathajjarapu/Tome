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
    # Formats AnyDoc handles, with Docling as the fallback for scanned PDFs.
    allowed_extensions: set[str] = {
        ".pdf", ".docx", ".doc", ".pptx", ".xlsx", ".epub", ".csv", ".md", ".txt", ".html",
    }


# Read once at import so a missing variable fails at startup, not at first request.
settings = Settings()
