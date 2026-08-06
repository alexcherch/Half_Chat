"""message soft delete (deleted flag)

Revision ID: 3a8f5e034ea9
Revises: 44281e2e40c7
Create Date: 2026-08-04 13:44:43.305887

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3a8f5e034ea9"
down_revision: Union[str, Sequence[str], None] = "44281e2e40c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "message",
        sa.Column("deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("message", "deleted")
