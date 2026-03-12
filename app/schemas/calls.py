from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CallCompleteRequest(BaseModel):
    external_call_id: str
    mc_number: str
    load_id: str | None = None
    final_rate: int | None = None
    outcome: str
    sentiment: str
    transcript_excerpt: str | None = None
    extracted_fields: dict[str, Any] = Field(default_factory=dict)


class CallCompleteResponse(BaseModel):
    external_call_id: str
    status: str
    load_status: str | None = None
    completed_at: datetime
