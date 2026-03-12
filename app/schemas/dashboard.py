from datetime import datetime

from pydantic import BaseModel

from app.schemas.metrics import MetricsSummaryResponse


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
    matched_loads_count: int
    outcome: str | None = None
    sentiment: str | None = None
    agreed_rate: int | None = None
    selected_load: DashboardLoadSnapshot | None = None
    negotiation_rounds: int
    transcript_excerpt: str | None = None


class DashboardDataResponse(BaseModel):
    summary: MetricsSummaryResponse
    load_status_counts: dict[str, int]
    recent_calls: list[DashboardRecentCall]
    last_updated_at: datetime


class DashboardLoginRequest(BaseModel):
    password: str


class DashboardLoginResponse(BaseModel):
    success: bool
