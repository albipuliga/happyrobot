from datetime import date, datetime

from pydantic import BaseModel


class LoadSearchRequest(BaseModel):
    external_call_id: str
    equipment_type: str
    origin: str
    destination: str | None = None
    pickup_date: date | None = None


class LoadSummary(BaseModel):
    load_id: str
    origin: str
    destination: str
    pickup_datetime: datetime
    delivery_datetime: datetime
    equipment_type: str
    loadboard_rate: int
    notes: str
    weight: int
    commodity_type: str
    num_of_pieces: int
    miles: int
    dimensions: str
    status: str


class LoadSearchResponse(BaseModel):
    matches: list[LoadSummary]
    best_match: LoadSummary | None = None
    summary_for_agent: str
