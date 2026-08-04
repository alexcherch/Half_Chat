"""add group_ban table

Revision ID: 0040ba98630d
Revises: ae1f8d451397
Create Date: 2026-08-04 13:12:59.261079

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0040ba98630d"
down_revision: Union[str, Sequence[str], None] = "ae1f8d451397"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "group_ban",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["chat_group.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_group_ban_group_id"), "group_ban", ["group_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_group_ban_group_id"), table_name="group_ban")
    op.drop_table("group_ban")
