from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Party(Base):
    __tablename__ = "parties"

    id: Mapped[int] = mapped_column(primary_key=True)
    election_id: Mapped[int] = mapped_column(ForeignKey("elections.id"))
    name: Mapped[str] = mapped_column(String(200))
    abbreviation: Mapped[str] = mapped_column(String(50))
    logo_url: Mapped[str | None] = mapped_column(String(500))
    website_url: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    program_text: Mapped[str | None] = mapped_column(Text)
    motion_summary: Mapped[str | None] = mapped_column(Text)
    current_seats: Mapped[int | None] = mapped_column(Integer)
    polled_seats: Mapped[int | None] = mapped_column(Integer)
    poll_updated_at: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    election: Mapped["Election"] = relationship(back_populates="parties")
    candidates: Mapped[list["Candidate"]] = relationship(back_populates="party")
    documents: Mapped[list["Document"]] = relationship(back_populates="party")
