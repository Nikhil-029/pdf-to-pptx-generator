from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # ── Directories ─────────────────────────────────────────────────────────
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    OUTPUT_DIR: Path = BASE_DIR / "outputs"

    # ── File constraints ────────────────────────────────────────────────────
    MAX_FILE_SIZE_MB: int = 20
    MAX_FILE_SIZE_BYTES: int = MAX_FILE_SIZE_MB * 1024 * 1024
    MIN_PAGES: int = 2
    MAX_PAGES: int = 50
    ALLOWED_EXTENSIONS: List[str] = [".pdf"]
    ALLOWED_CONTENT_TYPES: List[str] = ["application/pdf"]

    # ── Chunking ────────────────────────────────────────────────────────────
    CHUNK_TARGET_WORDS: int = 220
    CHUNK_MAX_WORDS: int = 300
    CHUNK_OVERLAP_WORDS: int = 30

    # ── LLM ─────────────────────────────────────────────────────────────────
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-20b"

    # ── MinIO / S3 ──────────────────────────────────────────────────────────
    MINIO_ENDPOINT: str = "http://localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET_UPLOADS: str = "pdf-uploads"
    MINIO_BUCKET_OUTPUTS: str = "pptx-outputs"

    # ── Redis / Celery ──────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Images ──────────────────────────────────────────────────────────────
    UNSPLASH_ACCESS_KEY: str = ""

    # ── CORS ─────────────────────────────────────────────────────────────────
    CORS_ORIGINS: List[str] = ["*"]

    # ── Presentation defaults ────────────────────────────────────────────────
    DEFAULT_TARGET_SLIDE_COUNT: int = 7


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
