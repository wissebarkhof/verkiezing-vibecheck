from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(primary_key=True)
    party_id: Mapped[int] = mapped_column(ForeignKey("parties.id"))
    name: Mapped[str] = mapped_column(String(200))
    position_on_list: Mapped[int] = mapped_column(Integer)
    photo_url: Mapped[str | None] = mapped_column(String(500))
    bio: Mapped[str | None] = mapped_column(Text)
    bluesky_handle: Mapped[str | None] = mapped_column(String(200))
    linkedin_url: Mapped[str | None] = mapped_column(String(500))
    social_summary: Mapped[str | None] = mapped_column(Text)
    linkedin_summary: Mapped[str | None] = mapped_column(Text)
    linkedin_headline: Mapped[str | None] = mapped_column(String(500))
    linkedin_current_position: Mapped[str | None] = mapped_column(String(500))
    linkedin_current_company: Mapped[str | None] = mapped_column(String(500))
    linkedin_experiences: Mapped[list | None] = mapped_column(JSONB)
    linkedin_education: Mapped[list | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    party: Mapped["Party"] = relationship(back_populates="candidates")
    posts: Mapped[list["SocialPost"]] = relationship(
        back_populates="candidate",
        cascade="all, delete-orphan",
    )
