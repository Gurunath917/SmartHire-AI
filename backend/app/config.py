"""
Application configuration — reads from .env via pydantic-settings.
Never hardcode secrets. All sensitive values come from environment variables.
"""
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional


class Settings(BaseSettings):
    # ── App ──────────────────────────────────────────────────────────────
    APP_NAME: str = "SmartHire AI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # ── Database ─────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/smarthire"

    # ── JWT ──────────────────────────────────────────────────────────────
    JWT_SECRET: str = "change_this_secret_in_production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # ── LLM / GenAI ──────────────────────────────────────────────────────
    LLM_API_KEY: Optional[str] = None
    LLM_MODEL: str = "gpt-3.5-turbo"
    OPENAI_API_BASE: Optional[str] = None  # For custom endpoints (e.g. Groq)

    # ── Vector Database ───────────────────────────────────────────────────
    VECTOR_DB_PATH: str = "./data/vector_store"
    VECTOR_DB_TYPE: str = "faiss"  # "faiss" or "chroma"

    # ── File Upload ───────────────────────────────────────────────────────
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 10  # 10 MB limit

    # ── CORS ─────────────────────────────────────────────────────────────
    FRONTEND_URL: str = "http://localhost:5173"
    ALLOWED_ORIGINS: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    @field_validator("DATABASE_URL")
    @classmethod
    def database_url_must_not_be_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("DATABASE_URL must be set in .env")
        return v

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore",
    }


# Single shared instance — import this everywhere
settings = Settings()
