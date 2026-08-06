"""user display_name

Revision ID: 314ddf4f621a
Revises: 9e7dddd378de
Create Date: 2026-08-06 16:15:34.744398

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "314ddf4f621a"
down_revision: Union[str, Sequence[str], None] = "9e7dddd378de"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("user", sa.Column("display_name", sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("user", "display_name")
