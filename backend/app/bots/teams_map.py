"""Azure AD tenant id to platform tenant mapping (M14).

Mirrors ``bots/tenant_map.py``: an admin registers their Microsoft 365 tenant
(``channelData.tenant.id`` from incoming Teams activities) so that messages from
any user in that org resolve to the correct platform tenant.

Owner: M14 — implement DB queries.
"""
import logging
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def get_tenant_for_teams(teams_tenant_id: str, db: AsyncSession) -> UUID | None:
    """Query teams_tenant_map table. Returns tenant_id or None."""
    result = await db.execute(
        text("SELECT tenant_id FROM teams_tenant_map WHERE teams_tenant_id = :ttid"),
        {"ttid": teams_tenant_id},
    )
    row = result.first()
    return row.tenant_id if row else None


async def register_teams_tenant(
    teams_tenant_id: str, tenant_id: UUID, db: AsyncSession
) -> None:
    """INSERT INTO teams_tenant_map."""
    await db.execute(
        text(
            "INSERT INTO teams_tenant_map (teams_tenant_id, tenant_id) "
            "VALUES (:ttid, :tid) ON CONFLICT (teams_tenant_id) DO NOTHING"
        ),
        {"ttid": teams_tenant_id, "tid": tenant_id},
    )
    await db.commit()
