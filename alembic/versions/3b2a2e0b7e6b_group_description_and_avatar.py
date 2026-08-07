"""group description and avatar

Revision ID: 3b2a2e0b7e6b
Revises: 314ddf4f621a
Create Date: 2026-08-07 13:13:53.936264

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3b2a2e0b7e6b"
down_revision: Union[str, Sequence[str], None] = "314ddf4f621a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("chat_group", sa.Column("description", sa.String(), nullable=True))
    op.add_column("chat_group", sa.Column("avatar_url", sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("chat_group", "avatar_url")
    op.drop_column("chat_group", "description")
