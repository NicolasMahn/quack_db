"""entra_oid on users; remove api_keys

Revision ID: 002
Revises: 001
Create Date: 2026-04-04

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("api_keys")
    op.add_column("users", sa.Column("entra_oid", sa.String(64), nullable=True))
    op.create_index("ix_users_entra_oid", "users", ["entra_oid"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_entra_oid", table_name="users")
    op.drop_column("users", "entra_oid")
    op.create_table(
        "api_keys",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("prefix", sa.String(16), nullable=False),
        sa.Column("key_hash", sa.String(128), nullable=False),
        sa.Column("revoked", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_api_keys_prefix", "api_keys", ["prefix"], unique=True)
    op.create_index("ix_api_keys_user_id", "api_keys", ["user_id"])
