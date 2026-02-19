"""add social_posts table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-16 15:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "social_posts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("candidate_id", sa.Integer(), nullable=False),
        # AT URI: unique identifier for a post on the AT Protocol network.
        # Used as upsert key — safe to re-run fetch_social.py without duplicates.
        sa.Column("uri", sa.String(length=500), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("posted_at", sa.DateTime(), nullable=False),
        sa.Column("like_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("reply_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("repost_count", sa.Integer(), server_default="0", nullable=False),
        # Resolved embed object. $type discriminates the embed kind:
        #   "app.bsky.embed.images#view"   — images with CDN thumb/fullsize URLs
        #   "app.bsky.embed.video#view"    — thumbnail + HLS playlist URL
        #   "app.bsky.embed.external#view" — link card (uri, title, description, thumb)
        #   "app.bsky.embed.record#view"   — quoted post reference
        sa.Column("embed_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("fetched_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uri", name="uq_social_posts_uri"),
    )
    op.create_index("ix_social_posts_candidate_id", "social_posts", ["candidate_id"])
    op.create_index("ix_social_posts_posted_at", "social_posts", ["posted_at"])


def downgrade() -> None:
    op.drop_index("ix_social_posts_posted_at", table_name="social_posts")
    op.drop_index("ix_social_posts_candidate_id", table_name="social_posts")
    op.drop_table("social_posts")
