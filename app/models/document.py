from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    party_id: Mapped[int] = mapped_column(ForeignKey("parties.id"))
    source_type: Mapped[str] = mapped_column(String(50))  # program, social, other
    content: Mapped[str] = mapped_column(Text)
    embedding = mapped_column(Vector(1536))  # text-embedding-3-small dimension
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    party: Mapped["Party"] = relationship(back_populates="documents")
