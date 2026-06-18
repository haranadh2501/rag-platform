"""
FastAPI application entry point.
Owner: M2 — extend this file. Do not remove existing routers.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 IISc RAG Platform starting up...")
    logger.info(f"   MOCK_N8N={settings.MOCK_N8N}")
    logger.info(f"   APP_ENV={settings.APP_ENV}")
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="IISc Grounded Agentic RAG Platform",
    version="1.0.0",
    description="Multi-tenant RAG platform API. See /docs for Swagger UI.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Rate limiting (in-process slowapi) ────────────────
# Routes opt in with @limiter.limit(...). slowapi reads app.state.limiter at
# request time; the handler turns an exceeded limit into a 429 (not a 500).
from slowapi import _rate_limit_exceeded_handler  # noqa: E402
from slowapi.errors import RateLimitExceeded  # noqa: E402
from app.core.rate_limit import limiter  # noqa: E402

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── Routers — wired up by M2 ──────────────────────────
from app.api import auth, admin, chat, webhooks, onboarding  # noqa: E402
app.include_router(auth.router,        prefix="/auth",        tags=["Auth"])
app.include_router(admin.router,       prefix="/admin",       tags=["Admin"])
app.include_router(chat.router,        prefix="/chat",        tags=["Chat"])
app.include_router(webhooks.router,    prefix="/webhooks",    tags=["Webhooks"])
app.include_router(onboarding.router,  prefix="/onboarding",  tags=["Onboarding"])

# ── MCP server (optional) ─────────────────────────────
# Exposes /chat/query as MCP tools for Claude Desktop & other MCP clients.
if settings.MCP_ENABLED:
    try:
        from app.mcp.server import mcp_router
        app.include_router(mcp_router, prefix="/mcp", tags=["MCP"])
        logger.info("   MCP server mounted at /mcp")
    except Exception as e:  # don't crash on optional dep
        logger.warning(f"   MCP server NOT mounted: {e}")


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check — pings the database and reports service status."""
    from sqlalchemy import text
    from app.core.database import engine

    database = "connected"
    overall = "ok"
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:  # don't 500 the health probe — report degraded
        logger.warning("Health check DB ping failed: %s", exc)
        database = "unreachable"
        overall = "degraded"

    return JSONResponse({
        "status": overall,
        "database": database,
        "n8n": "mocked" if settings.MOCK_N8N else "unchecked",
        "mock_n8n": settings.MOCK_N8N,
        "mcp_enabled": settings.MCP_ENABLED,
        "version": "1.0.0",
    })


@app.get("/", tags=["Health"])
async def root():
    return {"message": "IISc RAG Platform API", "docs": "/docs"}
