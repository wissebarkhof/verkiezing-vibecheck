"""add platform to social_posts

Revision ID: c1913b8250a6
Revises: 1b1b0e125970
Create Date: 2026-02-16 22:28:33.417971

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c1913b8250a6'
down_revision: Union[str, Sequence[str], None] = '1b1b0e125970'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('social_posts', sa.Column('platform', sa.String(length=20), server_default='bluesky', nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('social_posts', 'platform')
