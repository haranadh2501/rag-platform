"""M4: unified messaging schema

- users: add phone_number, slack_user_id identity columns
- conversations: make user_id NOT NULL; add UNIQUE(user_id, channel) constraint
- new: slack_workspace_map   (team_id → tenant_id, mirrors whatsapp_tenant_map)
- new: processed_requests    (webhook dedup table)
- new indexes on users, conversations, chat_messages, processed_requests

Revision ID: 0002_m4_messaging
Revises:     0001_initial
Create Date: 2026-06-17
Owner:       M4
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0002_m4_messaging"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    # ── users: identity columns ───────────────────────────────────────────────
    op.add_column("users", sa.Column("phone_number",  sa.String(20),  nullable=True))
    op.add_column("users", sa.Column("slack_user_id", sa.String(255), nullable=True))

    op.create_unique_constraint("uq_users_phone_number",  "users", ["phone_number"])
    op.create_unique_constraint("uq_users_slack_user_id", "users", ["slack_user_id"])

    op.create_index(
        "idx_users_phone",
        "users", ["phone_number"],
        postgresql_where=sa.text("phone_number IS NOT NULL"),
    )
    op.create_index(
        "idx_users_slack",
        "users", ["slack_user_id"],
        postgresql_where=sa.text("slack_user_id IS NOT NULL"),
    )

    # ── conversations: enforce one conversation per user per channel ──────────
    # NOTE: will fail if existing rows have user_id = NULL.
    # Clean up orphan rows first:
    #   DELETE FROM conversations WHERE user_id IS NULL;
    op.alter_column(
        "conversations", "user_id",
        existing_type=UUID(as_uuid=True),
        nullable=False,
    )

    op.create_unique_constraint(
        "uq_conversations_user_channel",
        "conversations",
        ["user_id", "channel"],
    )

    op.create_index(
        "idx_conv_tenant",
        "conversations", ["tenant_id", "created_at"],
        postgresql_using="btree",
        if_not_exists=True,   # index may already exist from a partial prior run
    )

    # ── chat_messages: history load index ────────────────────────────────────
    op.create_index(
        "idx_messages_conv_time",
        "chat_messages", ["conversation_id", "created_at"],
        if_not_exists=True,
    )

    # ── slack_workspace_map ───────────────────────────────────────────────────
    op.create_table(
        "slack_workspace_map",
        sa.Column("team_id",    sa.String(64),  nullable=False),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("team_id", name="pk_slack_workspace_map"),
    )

    # ── processed_requests ───────────────────────────────────────────────────
    op.create_table(
        "processed_requests",
        sa.Column("request_id",  sa.String(255), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("request_id", name="pk_processed_requests"),
    )

    op.create_index(
        "idx_preq_received",
        "processed_requests", ["received_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_preq_received",       table_name="processed_requests")
    op.drop_table("processed_requests")

    op.drop_table("slack_workspace_map")

    op.drop_index("idx_messages_conv_time",  table_name="chat_messages")
    op.drop_index("idx_conv_tenant",         table_name="conversations")
    op.drop_constraint("uq_conversations_user_channel", "conversations", type_="unique")
    op.alter_column(
        "conversations", "user_id",
        existing_type=UUID(as_uuid=True),
        nullable=True,
    )

    op.drop_index("idx_users_slack", table_name="users")
    op.drop_index("idx_users_phone", table_name="users")
    op.drop_constraint("uq_users_slack_user_id", "users", type_="unique")
    op.drop_constraint("uq_users_phone_number",  "users", type_="unique")
    op.drop_column("users", "slack_user_id")
    op.drop_column("users", "phone_number")
