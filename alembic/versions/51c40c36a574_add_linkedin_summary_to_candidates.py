"""add linkedin_summary to candidates

Revision ID: 51c40c36a574
Revises: c3d4e5f6a7b8
Create Date: 2026-02-16 21:27:08.699332

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '51c40c36a574'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('candidates', sa.Column('linkedin_summary', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('candidates', 'linkedin_summary')
