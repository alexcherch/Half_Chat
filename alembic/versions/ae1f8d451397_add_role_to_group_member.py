"""add role to group_member

Revision ID: ae1f8d451397
Revises: 3884a6a57eb1
Create Date: 2026-08-04 12:59:52.435198

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ae1f8d451397"
down_revision: Union[str, Sequence[str], None] = "3884a6a57eb1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "group_member",
        sa.Column("role", sa.String(), nullable=False, server_default="member"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("group_member", "role")
