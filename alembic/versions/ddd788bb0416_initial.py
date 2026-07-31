"""initial

Revision ID: ddd788bb0416
Revises:
Create Date: 2026-07-30 13:54:56.516060

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ddd788bb0416"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "user",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_username", "user", ["username"], unique=True)

    op.create_table(
        "chat_group",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chat_group_name", "chat_group", ["name"])

    op.create_table(
        "group_member",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["chat_group.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_group_member_group_id", "group_member", ["group_id"])

    op.create_table(
        "message",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("text", sa.String(), nullable=False),
        sa.Column("timestamp", sa.String(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["chat_group.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_message_group_id", "message", ["group_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_message_group_id", table_name="message")
    op.drop_table("message")
    op.drop_index("ix_group_member_group_id", table_name="group_member")
    op.drop_table("group_member")
    op.drop_index("ix_chat_group_name", table_name="chat_group")
    op.drop_table("chat_group")
    op.drop_index("ix_user_username", table_name="user")
    op.drop_table("user")
