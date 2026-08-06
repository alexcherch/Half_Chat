"""user avatar_url

Revision ID: 9e7dddd378de
Revises: 3a8f5e034ea9
Create Date: 2026-08-06 15:25:35.653292

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9e7dddd378de"
down_revision: Union[str, Sequence[str], None] = "3a8f5e034ea9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("user", sa.Column("avatar_url", sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("user", "avatar_url")
