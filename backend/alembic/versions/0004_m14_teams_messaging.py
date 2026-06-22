"""M14: Microsoft Teams messaging schema

- users: add teams_user_id identity column (mirrors slack_user_id / phone_number)
- new: teams_tenant_map  (Azure AD tenant id → tenant_id, mirrors whatsapp_tenant_map)

Dedup reuses the existing processed_requests table from 0002.

Revision ID: 0004_m14_teams_messaging
Revises:     0003_uuid_defaults
Create Date: 2026-06-21
Owner:       M14
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0004_m14_teams_messaging"
down_revision: Union[str, None] = "0003_uuid_defaults"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users: Teams identity column ──────────────────────────────────────────
    op.add_column("users", sa.Column("teams_user_id", sa.String(255), nullable=True))
    op.create_unique_constraint("uq_users_teams_user_id", "users", ["teams_user_id"])
    op.create_index(
        "idx_users_teams",
        "users", ["teams_user_id"],
        postgresql_where=sa.text("teams_user_id IS NOT NULL"),
    )

    # ── teams_tenant_map ──────────────────────────────────────────────────────
    # Azure AD tenant id (channelData.tenant.id) → platform tenant_id.
    op.create_table(
        "teams_tenant_map",
        sa.Column("teams_tenant_id", sa.String(64), nullable=False),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("teams_tenant_id", name="pk_teams_tenant_map"),
    )


def downgrade() -> None:
    op.drop_table("teams_tenant_map")

    op.drop_index("idx_users_teams", table_name="users")
    op.drop_constraint("uq_users_teams_user_id", "users", type_="unique")
    op.drop_column("users", "teams_user_id")
