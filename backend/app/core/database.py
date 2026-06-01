"""Async SQLAlchemy engine + session factory + FastAPI dependency.

Owner: M2 — core infrastructure shared by every router that touches the DB.

Usage in a route:
    from app.core.database import get_db
    async def handler(db: AsyncSession = Depends(get_db)): ...
"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

# `pool_pre_ping` recycles dead connections (e.g. after Postgres restarts in
# docker compose) instead of handing a stale socket to a request.
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a session, rolling back on error and always closing it."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
