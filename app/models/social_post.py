from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SocialPost(Base):
    __tablename__ = "social_posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"))
    platform: Mapped[str] = mapped_column(String(20), default="bluesky")  # "bluesky" or "linkedin"
    # AT URI (Bluesky) or LinkedIn post URL. Used as the upsert key.
    uri: Mapped[str] = mapped_column(String(500), unique=True)
    text: Mapped[str] = mapped_column(Text)
    posted_at: Mapped[datetime] = mapped_column(DateTime)
    like_count: Mapped[int] = mapped_column(Integer, default=0)
    reply_count: Mapped[int] = mapped_column(Integer, default=0)
    repost_count: Mapped[int] = mapped_column(Integer, default=0)
    # Resolved embed object from the API. Type discriminated by embed_json["$type"]:
    #   "app.bsky.embed.images#view"   → images[]{thumb, fullsize, alt, aspectRatio}
    #   "app.bsky.embed.video#view"    → thumbnail, playlist (HLS)
    #   "app.bsky.embed.external#view" → external{uri, title, description, thumb}
    #   "app.bsky.embed.record#view"   → record reference (quoted post)
    embed_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    candidate: Mapped["Candidate"] = relationship(back_populates="posts")
