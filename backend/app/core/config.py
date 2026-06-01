"""Application configuration — reads from .env file.

Locked model stack (see ARCHITECTURE.md):
    Embeddings   : Voyage voyage-4-large (1024 dims, FREE 200M tokens)
    Reranker     : Voyage rerank-2.5
    Generation   : DeepSeek V4 Flash (OpenAI-compatible)
    Self-check   : Gemini 3.5 Flash
    Hard fallback: DeepSeek V4 Pro
    Insurance    : OpenAI ($5 prepaid + $10 hard cap)
"""
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── App ──────────────────────────────────────────────────────────
    APP_ENV: str = "development"
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    # ── Mock mode ────────────────────────────────────────────────────
    MOCK_N8N: bool = True

    # ── Database ─────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://raguser:changeme@localhost:5432/ragplatform"

    @property
    def SYNC_DATABASE_URL(self) -> str:
        """Sync (psycopg2) DSN derived from DATABASE_URL — used by Alembic, which
        runs migrations synchronously."""
        return self.DATABASE_URL.replace("+asyncpg", "+psycopg2")

    # ── n8n ──────────────────────────────────────────────────────────
    N8N_BASE_URL: str = "http://localhost:5678"
    N8N_INGEST_WEBHOOK_URL: str = "http://localhost:5678/webhook/ingest"
    N8N_RETRIEVE_WEBHOOK_URL: str = "http://localhost:5678/webhook/retrieve"
    N8N_EPHEMERAL_INGEST_WEBHOOK_URL: str = "http://localhost:5678/webhook/ingest-ephemeral"
    N8N_CALLBACK_TOKEN: str = "change-me-shared-secret-with-n8n"

    # ── Voyage AI (embeddings + rerank) ──────────────────────────────
    VOYAGE_API_KEY: str = ""
    VOYAGE_EMBEDDING_MODEL: str = "voyage-4-large"     # 1024 dims
    VOYAGE_RERANK_MODEL: str = "rerank-2.5"

    # ── DeepSeek (generation) ────────────────────────────────────────
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_FLASH_MODEL: str = "deepseek-v4-flash"
    DEEPSEEK_PRO_MODEL: str = "deepseek-v4-pro"

    # ── Gemini (self-check) ──────────────────────────────────────────
    GEMINI_API_KEY: str = ""
    GEMINI_SELFCHECK_MODEL: str = "gemini-3.5-flash"

    # ── OpenAI (insurance + vision OCR) ──────────────────────────────
    OPENAI_API_KEY: str = ""
    OPENAI_VISION_MODEL: str = "gpt-4o-mini"
    OPENAI_HARD_CAP_USD: float = 10.0

    # ── Twilio (WhatsApp) ────────────────────────────────────────────
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_WHATSAPP_NUMBER: str = "whatsapp:+14155238886"

    # ── Slack (stretch) ──────────────────────────────────────────────
    SLACK_BOT_TOKEN: str = ""
    SLACK_SIGNING_SECRET: str = ""

    # ── File upload limits ───────────────────────────────────────────
    UPLOAD_DIR: str = "/uploads"
    MAX_UPLOAD_BYTES: int = 26_214_400               # 25 MB
    MAX_WHATSAPP_UPLOAD_BYTES: int = 10_485_760      # 10 MB
    MAX_PAGES_PER_DOC: int = 500
    MAX_BYTES_PER_TENANT: int = 1_073_741_824        # 1 GB
    MAX_UPLOADS_PER_HOUR: int = 20
    ALLOWED_MIME_TYPES: str = (
        "application/pdf,"
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document,"
        "text/plain,image/png,image/jpeg"
    )

    @property
    def allowed_mime_set(self) -> set[str]:
        return {m.strip() for m in self.ALLOWED_MIME_TYPES.split(",") if m.strip()}

    # ── Seed ─────────────────────────────────────────────────────────
    SEED_ADMIN_EMAIL: str = "admin@iisc-demo.com"
    SEED_ADMIN_PASSWORD: str = "changeme"
    SEED_TENANT_NAME: str = "IISc Demo"
    SEED_TENANT_SLUG: str = "iisc-demo"

    # ── MCP server ───────────────────────────────────────────────────
    MCP_ENABLED: bool = True
    MCP_API_KEY: str = "change-me-mcp-shared-secret"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"   # tolerate extra env vars without crashing


settings = Settings()
