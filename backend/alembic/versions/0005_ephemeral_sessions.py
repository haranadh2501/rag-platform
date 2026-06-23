"""Add ephemeral_sessions table for WhatsApp ephemeral document-analysis sessions.

Revision ID: 0005_ephemeral_sessions
Revises:     0004_m14_teams_messaging
Create Date: 2026-06-22
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0005_ephemeral_sessions"
down_revision: Union[str, None] = "0004_m14_teams_messaging"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ephemeral_sessions",
        sa.Column("id",              UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id",       UUID(as_uuid=True), sa.ForeignKey("tenants.id",       ondelete="CASCADE"), nullable=False),
        sa.Column("user_id",         UUID(as_uuid=True), sa.ForeignKey("users.id",         ondelete="CASCADE"), nullable=False),
        sa.Column("conversation_id", UUID(as_uuid=True), sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("n8n_session_id",  UUID(as_uuid=True), nullable=False),
        sa.Column("status",          sa.String(30),  nullable=False, server_default="awaiting_document"),
        sa.Column("total_chunks",    sa.Integer(),   nullable=False, server_default="0"),
        sa.Column("doc_count",       sa.Integer(),   nullable=False, server_default="0"),
        sa.Column("expires_at",      sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at",      sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_ephemeral_sessions"),
    )
    # Fast user lookup
    op.create_index("idx_ephemeral_sessions_user", "ephemeral_sessions", ["user_id"])
    # Enforce one active session per user at DB level
    op.create_index("idx_ephemeral_sessions_one_per_user", "ephemeral_sessions", ["user_id"], unique=True)


def downgrade() -> None:
    op.drop_index("idx_ephemeral_sessions_one_per_user", table_name="ephemeral_sessions")
    op.drop_index("idx_ephemeral_sessions_user",         table_name="ephemeral_sessions")
    op.drop_table("ephemeral_sessions")
