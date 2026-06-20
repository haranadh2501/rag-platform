"""Add gen_random_uuid() server defaults to UUID primary key columns.

The initial migration created UUID PK columns without a DB-level DEFAULT.
Raw-SQL INSERTs (e.g. in message_service) omit the id column and rely on
the DB to generate it. This migration wires that up.

Revision ID: 0003_uuid_defaults
Revises:     0002_m4_messaging
Create Date: 2026-06-20
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_uuid_defaults"
down_revision: Union[str, None] = "0002_m4_messaging"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLES = [
    "tenants",
    "users",
    "documents",
    "conversations",
    "chat_messages",
]


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    for table in _TABLES:
        op.execute(
            f"ALTER TABLE {table} ALTER COLUMN id SET DEFAULT gen_random_uuid()"
        )


def downgrade() -> None:
    for table in _TABLES:
        op.execute(f"ALTER TABLE {table} ALTER COLUMN id DROP DEFAULT")
