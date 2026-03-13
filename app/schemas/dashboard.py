from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.schemas.metrics import MetricsSummaryResponse

Tone = Literal["positive", "negative", "pending"]


class DashboardBreakdownItem(BaseModel):
    label: str
    count: int
    tone: Tone


class DashboardLoadSnapshot(BaseModel):
    load_id: str
    origin: str
    destination: str
    equipment_type: str
    loadboard_rate: int
    status: str


class DashboardRecentCall(BaseModel):
    external_call_id: str
    started_at: datetime
    ended_at: datetime | None = None
    mc_number: str | None = None
    verification_passed: bool | None = None
    verification_tone: Tone
    matched_loads_count: int
    outcome: str | None = None
    outcome_tone: Tone
    sentiment: str | None = None
    sentiment_tone: Tone
    agreed_rate: int | None = None
    selected_load: DashboardLoadSnapshot | None = None
    negotiation_rounds: int
    transcript_excerpt: str | None = None


class DashboardDataResponse(BaseModel):
    summary: MetricsSummaryResponse
    load_status_counts: dict[str, int]
    outcome_breakdown: list[DashboardBreakdownItem]
    sentiment_breakdown: list[DashboardBreakdownItem]
    load_status_breakdown: list[DashboardBreakdownItem]
    recent_calls: list[DashboardRecentCall]
    total_calls: int
    page_size: int
    last_updated_at: datetime


class DashboardLoginRequest(BaseModel):
    password: str


class DashboardLoginResponse(BaseModel):
    success: bool
