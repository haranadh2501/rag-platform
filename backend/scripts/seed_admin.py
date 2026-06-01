"""Seed script — creates the demo tenant + super_admin user.

Owner: M2. Idempotent: safe to run repeatedly (it only inserts what's missing).

Run from the backend/ directory (or inside the backend container, WORKDIR=/app):
    python -m scripts.seed_admin

Reads from .env: SEED_ADMIN_EMAIL, SEED_ADMIN_PASSWORD, SEED_TENANT_NAME,
SEED_TENANT_SLUG.
"""
import asyncio
import logging
import os
import sys

# Put backend/ on sys.path so `import app...` works when run as a script.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.database import AsyncSessionLocal, engine  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.models.models import Tenant, User  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_admin")


async def create_admin() -> None:
    logger.info("Seeding tenant '%s' (%s) + admin %s",
                settings.SEED_TENANT_NAME, settings.SEED_TENANT_SLUG, settings.SEED_ADMIN_EMAIL)

    async with AsyncSessionLocal() as db:
        # 1. Tenant (by slug)
        tenant = (
            await db.execute(select(Tenant).where(Tenant.slug == settings.SEED_TENANT_SLUG))
        ).scalar_one_or_none()
        if tenant is None:
            tenant = Tenant(name=settings.SEED_TENANT_NAME, slug=settings.SEED_TENANT_SLUG)
            db.add(tenant)
            await db.flush()  # assign tenant.id
            logger.info("  + created tenant %s", tenant.id)
        else:
            logger.info("  = tenant already exists (%s)", tenant.id)

        # 2. Admin user (by email)
        user = (
            await db.execute(select(User).where(User.email == settings.SEED_ADMIN_EMAIL))
        ).scalar_one_or_none()
        if user is None:
            user = User(
                tenant_id=tenant.id,
                email=settings.SEED_ADMIN_EMAIL,
                hashed_password=get_password_hash(settings.SEED_ADMIN_PASSWORD),
                role="super_admin",
            )
            db.add(user)
            logger.info("  + created super_admin %s", settings.SEED_ADMIN_EMAIL)
        else:
            logger.info("  = user already exists (%s)", user.id)

        await db.commit()

    await engine.dispose()
    logger.info("✅ Seed complete")


if __name__ == "__main__":
    asyncio.run(create_admin())
