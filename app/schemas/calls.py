from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class CallCompleteRequest(BaseModel):
    external_call_id: str
    mc_number: str | None = None
    load_id: str | None = None
    final_rate: int | None = None
    outcome: str
    sentiment: str
    transcript_excerpt: str | None = None
    extracted_fields: dict[str, Any] = Field(default_factory=dict)

    @field_validator("mc_number", mode="before")
    @classmethod
    def coerce_mc_number(cls, v):
        if v is None or v == "" or v == "null":
            return None
        return str(v).strip()

    @field_validator("load_id", "transcript_excerpt", mode="before")
    @classmethod
    def empty_string_to_none(cls, v):
        if v is None or v == "" or v == "null":
            return None
        return v

    @field_validator("final_rate", mode="before")
    @classmethod
    def coerce_final_rate(cls, v):
        if v is None or v == "" or v == "null":
            return None
        return int(v)


class CallCompleteResponse(BaseModel):
    external_call_id: str
    status: str
    load_status: str | None = None
    completed_at: datetime