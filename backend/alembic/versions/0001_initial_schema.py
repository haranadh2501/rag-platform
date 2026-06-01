"""initial core schema (auth + relational tables)

Owner: M2.

Creates the relational/core tables that back M2's models. Each CREATE is guarded
by an existence check, so this migration is idempotent and coexists with
`database/init.sql` (which bootstraps the same schema on docker compose first
boot): on an already-initialised DB it simply stamps the revision and skips.

NOT created here: `document_chunks` and `ephemeral_chunks`. Those carry pgvector
`vector(1024)` columns that aren't modelled in the ORM and are owned by
`database/init.sql` (M7) / the n8n ingestion path (M5).

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-01
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Tables this migration owns, in dependency (create) order.
_TABLES = [
    "tenants",
    "users",
    "documents",
    "conversations",
    "chat_messages",
    "upload_audit",
    "whatsapp_tenant_map",
]


def _existing() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    existing = _existing()

    if "tenants" not in existing:
        op.create_table(
            "tenants",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("slug", sa.String(100), nullable=False, unique=True),
            sa.Column("plan", sa.String(50), server_default="free"),
            sa.Column("is_active", sa.Boolean, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        )

    if "users" not in existing:
        op.create_table(
            "users",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "tenant_id",
                UUID(as_uuid=True),
                sa.ForeignKey("tenants.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("email", sa.String(255), nullable=False, unique=True),
            sa.Column("hashed_password", sa.String(255), nullable=False),
            sa.Column("role", sa.String(50), server_default="user"),
            sa.Column("is_active", sa.Boolean, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        )

    if "documents" not in existing:
        op.create_table(
            "documents",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "tenant_id",
                UUID(as_uuid=True),
                sa.ForeignKey("tenants.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("uploaded_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("title", sa.String(500), nullable=False),
            sa.Column("source_type", sa.String(50), nullable=False),
            sa.Column("source_url", sa.Text, nullable=True),
            sa.Column("file_path", sa.Text, nullable=True),
            sa.Column("status", sa.String(50), server_default="pending"),
            sa.Column("chunk_count", sa.Integer, server_default="0"),
            sa.Column("error_message", sa.Text, nullable=True),
            sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        )

    if "conversations" not in existing:
        op.create_table(
            "conversations",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "tenant_id",
                UUID(as_uuid=True),
                sa.ForeignKey("tenants.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("title", sa.String(500), nullable=True),
            sa.Column("channel", sa.String(50), server_default="web"),
            sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        )

    if "chat_messages" not in existing:
        op.create_table(
            "chat_messages",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "conversation_id",
                UUID(as_uuid=True),
                sa.ForeignKey("conversations.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("role", sa.String(20), nullable=False),
            sa.Column("content", sa.Text, nullable=False),
            sa.Column("sources", sa.JSON, server_default=sa.text("'[]'")),
            sa.Column("faithfulness", sa.Numeric(3, 2), nullable=True),
            sa.Column("requires_clarification", sa.Boolean, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        )

    if "upload_audit" not in existing:
        op.create_table(
            "upload_audit",
            sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
            sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
            sa.Column("uploaded_at", sa.DateTime, server_default=sa.func.now()),
            sa.Column("bytes", sa.BigInteger, server_default="0"),
        )
        op.create_index(
            "idx_audit_tenant_time", "upload_audit", ["tenant_id", "uploaded_at"]
        )

    if "whatsapp_tenant_map" not in existing:
        op.create_table(
            "whatsapp_tenant_map",
            sa.Column("phone_number", sa.String(20), primary_key=True),
            sa.Column(
                "tenant_id",
                UUID(as_uuid=True),
                sa.ForeignKey("tenants.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        )


def downgrade() -> None:
    # Drop in reverse dependency order; only touch tables this migration owns.
    for table in reversed(_TABLES):
        op.drop_table(table)
