"""add linkedin profile fields to candidates

Revision ID: f3a1b2c4d5e6
Revises: 51c40c36a574
Create Date: 2026-02-19 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = 'f3a1b2c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'eb524fd99adc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('candidates', sa.Column('linkedin_headline', sa.String(500), nullable=True))
    op.add_column('candidates', sa.Column('linkedin_current_position', sa.String(500), nullable=True))
    op.add_column('candidates', sa.Column('linkedin_current_company', sa.String(500), nullable=True))
    op.add_column('candidates', sa.Column('linkedin_experiences', JSONB, nullable=True))
    op.add_column('candidates', sa.Column('linkedin_education', JSONB, nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('candidates', 'linkedin_education')
    op.drop_column('candidates', 'linkedin_experiences')
    op.drop_column('candidates', 'linkedin_current_company')
    op.drop_column('candidates', 'linkedin_current_position')
    op.drop_column('candidates', 'linkedin_headline')
