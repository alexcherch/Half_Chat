"""user block list

Revision ID: c69712938c7f
Revises: 3b2a2e0b7e6b
Create Date: 2026-08-07 13:23:32.128795

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c69712938c7f"
down_revision: Union[str, Sequence[str], None] = "3b2a2e0b7e6b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "user_block",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("blocker_id", sa.Integer(), nullable=False),
        sa.Column("blocked_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["blocked_id"],
            ["user.id"],
        ),
        sa.ForeignKeyConstraint(
            ["blocker_id"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("blocker_id", "blocked_id", name="uq_user_block_pair"),
    )
    op.create_index(op.f("ix_user_block_blocked_id"), "user_block", ["blocked_id"], unique=False)
    op.create_index(op.f("ix_user_block_blocker_id"), "user_block", ["blocker_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_user_block_blocker_id"), table_name="user_block")
    op.drop_index(op.f("ix_user_block_blocked_id"), table_name="user_block")
    op.drop_table("user_block")
