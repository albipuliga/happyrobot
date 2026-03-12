from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class CallSession(Base):
    __tablename__ = "call_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_call_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    caller_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    mc_number: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    selected_load_id: Mapped[int | None] = mapped_column(ForeignKey("loads.id"), nullable=True)
    verification_passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    matched_loads_count: Mapped[int] = mapped_column(Integer, default=0)
    agreed_rate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    outcome: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sentiment: Mapped[str | None] = mapped_column(String(32), nullable=True)
    transcript_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_fields: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    selected_load = relationship("Load", back_populates="call_sessions")
    negotiation_events = relationship("NegotiationEvent", back_populates="call_session")
