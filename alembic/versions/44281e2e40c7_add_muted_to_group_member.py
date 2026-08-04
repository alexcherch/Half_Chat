"""add muted to group_member

Revision ID: 44281e2e40c7
Revises: 0040ba98630d
Create Date: 2026-08-04 13:18:30.119192

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "44281e2e40c7"
down_revision: Union[str, Sequence[str], None] = "0040ba98630d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "group_member",
        sa.Column("muted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("group_member", "muted")
