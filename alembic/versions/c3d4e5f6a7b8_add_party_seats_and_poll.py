"""add party seats and poll fields

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-02-16 15:30:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("parties", sa.Column("current_seats", sa.Integer(), nullable=True))
    op.add_column("parties", sa.Column("polled_seats", sa.Integer(), nullable=True))
    op.add_column("parties", sa.Column("poll_updated_at", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("parties", "poll_updated_at")
    op.drop_column("parties", "polled_seats")
    op.drop_column("parties", "current_seats")
