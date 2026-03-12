from datetime import datetime

from sqlalchemy import Boolean, DateTime, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CarrierCheck(Base):
    __tablename__ = "carrier_checks"

    id: Mapped[int] = mapped_column(primary_key=True)
    mc_number: Mapped[str] = mapped_column(String(32), index=True)
    dot_number: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    legal_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    dba_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    authority_status: Mapped[str | None] = mapped_column(String(128), nullable=True)
    eligible: Mapped[bool] = mapped_column(Boolean, default=False)
    failure_reasons: Mapped[list[str]] = mapped_column(JSON, default=list)
    snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    verification_source: Mapped[str] = mapped_column(String(32), default="live")
    checked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
