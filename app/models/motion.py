from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Motion(Base):
    __tablename__ = "motions"

    id: Mapped[int] = mapped_column(primary_key=True)
    election_id: Mapped[int] = mapped_column(ForeignKey("elections.id"))
    # Notubiz module_item ID — used as upsert key to prevent duplicates on re-run.
    notubiz_item_id: Mapped[int] = mapped_column(Integer, unique=True)
    title: Mapped[str] = mapped_column(Text)
    motion_type: Mapped[str | None] = mapped_column(String(50))  # "Motie" / "Amendement"
    result: Mapped[str | None] = mapped_column(String(50))  # "Aangenomen" / "Verworpen" / null
    submission_date: Mapped[date | None] = mapped_column(Date)
    resolution_date: Mapped[date | None] = mapped_column(Date)
    toelichting: Mapped[str | None] = mapped_column(Text)  # raw HTML vote explanation
    document_url: Mapped[str | None] = mapped_column(String(500))
    resolution_document_url: Mapped[str | None] = mapped_column(String(500))
    meeting_event_id: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    election: Mapped["Election"] = relationship(back_populates="motions")
    parties: Mapped[list["MotionParty"]] = relationship(
        back_populates="motion", cascade="all, delete-orphan"
    )
    candidates: Mapped[list["MotionCandidate"]] = relationship(
        back_populates="motion", cascade="all, delete-orphan"
    )


class MotionParty(Base):
    __tablename__ = "motion_parties"

    id: Mapped[int] = mapped_column(primary_key=True)
    motion_id: Mapped[int] = mapped_column(ForeignKey("motions.id"))
    party_id: Mapped[int | None] = mapped_column(ForeignKey("parties.id"))
    notubiz_party_name: Mapped[str] = mapped_column(String(200))

    motion: Mapped["Motion"] = relationship(back_populates="parties")
    party: Mapped["Party | None"] = relationship()


class MotionCandidate(Base):
    __tablename__ = "motion_candidates"

    id: Mapped[int] = mapped_column(primary_key=True)
    motion_id: Mapped[int] = mapped_column(ForeignKey("motions.id"))
    candidate_id: Mapped[int | None] = mapped_column(ForeignKey("candidates.id"))
    notubiz_person_name: Mapped[str] = mapped_column(String(200))
    notubiz_person_id: Mapped[int | None] = mapped_column(Integer)

    motion: Mapped["Motion"] = relationship(back_populates="candidates")
    candidate: Mapped["Candidate | None"] = relationship()
