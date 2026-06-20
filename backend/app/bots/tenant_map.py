"""
Phone number to tenant ID mapping.
Owner: M12 — implement DB queries.
"""
import logging
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def get_tenant_for_phone(phone_number: str, db: AsyncSession) -> UUID | None:
    """Query whatsapp_tenant_map table. Returns tenant_id or None."""
    result = await db.execute(
        text("SELECT tenant_id FROM whatsapp_tenant_map WHERE phone_number = :phone"),
        {"phone": phone_number}
    )
    row = result.first()
    return row.tenant_id if row else None


async def register_phone_for_tenant(phone_number: str, tenant_id: UUID, db: AsyncSession) -> None:
    """INSERT INTO whatsapp_tenant_map."""
    await db.execute(
        text("INSERT INTO whatsapp_tenant_map (phone_number, tenant_id) VALUES (:phone, :tid) ON CONFLICT (phone_number) DO NOTHING"),
        {"phone": phone_number, "tid": tenant_id}
    )
    await db.commit()
