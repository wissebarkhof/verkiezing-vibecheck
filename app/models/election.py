from datetime import date, datetime

from sqlalchemy import Date, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Election(Base):
    __tablename__ = "elections"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    city: Mapped[str] = mapped_column(String(100))
    date: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    parties: Mapped[list["Party"]] = relationship(back_populates="election")
    topic_comparisons: Mapped[list["TopicComparison"]] = relationship(
        back_populates="election"
    )
    motions: Mapped[list["Motion"]] = relationship(back_populates="election")
    polls: Mapped[list["Poll"]] = relationship(back_populates="election")
