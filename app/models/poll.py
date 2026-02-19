from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Poll(Base):
    __tablename__ = "polls"

    id: Mapped[int] = mapped_column(primary_key=True)
    election_id: Mapped[int] = mapped_column(ForeignKey("elections.id"))
    source_name: Mapped[str] = mapped_column(String(200))
    source_url: Mapped[str] = mapped_column(String(500))
    source_type: Mapped[str] = mapped_column(String(50))  # e.g. "onderzoek_amsterdam", "manual"
    field_start: Mapped[date | None] = mapped_column(Date)
    field_end: Mapped[date] = mapped_column(Date)
    published_at: Mapped[date | None] = mapped_column(Date)
    sample_size: Mapped[int | None] = mapped_column(Integer)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("election_id", "source_url", "field_end", name="uq_poll_source_edition"),
    )

    election: Mapped["Election"] = relationship(back_populates="polls")
    results: Mapped[list["PollResult"]] = relationship(
        back_populates="poll", cascade="all, delete-orphan"
    )


class PollResult(Base):
    __tablename__ = "poll_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    poll_id: Mapped[int] = mapped_column(ForeignKey("polls.id"))
    party_id: Mapped[int | None] = mapped_column(ForeignKey("parties.id"))
    party_name_raw: Mapped[str] = mapped_column(String(200))
    percentage: Mapped[float | None] = mapped_column(Float)
    seats: Mapped[int | None] = mapped_column(Integer)

    poll: Mapped["Poll"] = relationship(back_populates="results")
    party: Mapped["Party | None"] = relationship()
