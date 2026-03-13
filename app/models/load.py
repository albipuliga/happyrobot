from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.state_vocab import LoadStatus


class Load(Base):
    __tablename__ = "loads"

    id: Mapped[int] = mapped_column(primary_key=True)
    load_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    origin: Mapped[str] = mapped_column(String(128))
    destination: Mapped[str] = mapped_column(String(128))
    pickup_datetime: Mapped[datetime] = mapped_column(DateTime)
    delivery_datetime: Mapped[datetime] = mapped_column(DateTime)
    equipment_type: Mapped[str] = mapped_column(String(64), index=True)
    loadboard_rate: Mapped[int] = mapped_column(Integer)
    max_rate: Mapped[int] = mapped_column(Integer)
    notes: Mapped[str] = mapped_column(Text)
    weight: Mapped[int] = mapped_column(Integer)
    commodity_type: Mapped[str] = mapped_column(String(128))
    num_of_pieces: Mapped[int] = mapped_column(Integer)
    miles: Mapped[int] = mapped_column(Integer)
    dimensions: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), default=LoadStatus.AVAILABLE.value, index=True)
    broker_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    call_sessions = relationship("CallSession", back_populates="selected_load")
    negotiation_events = relationship("NegotiationEvent", back_populates="load")
