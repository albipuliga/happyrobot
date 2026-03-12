from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class NegotiationEvent(Base):
    __tablename__ = "negotiation_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    call_session_id: Mapped[int] = mapped_column(ForeignKey("call_sessions.id"), index=True)
    load_id: Mapped[int] = mapped_column(ForeignKey("loads.id"), index=True)
    round_number: Mapped[int] = mapped_column(Integer)
    carrier_offer: Mapped[int] = mapped_column(Integer)
    broker_counter: Mapped[int | None] = mapped_column(Integer, nullable=True)
    decision: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    call_session = relationship("CallSession", back_populates="negotiation_events")
    load = relationship("Load", back_populates="negotiation_events")
