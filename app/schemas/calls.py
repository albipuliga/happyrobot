from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.state_vocab import CallOutcome, CallSentiment


OUTCOME_ALIASES = {
    "accepted": CallOutcome.BOOKED.value,
    "agreed": CallOutcome.BOOKED.value,
    "agreement_reached": CallOutcome.BOOKED.value,
    "transfer_ready": CallOutcome.BOOKED.value,
    "rejected": CallOutcome.REJECTED_RATE.value,
    "failed_verification": CallOutcome.CARRIER_INELIGIBLE.value,
    "ineligible": CallOutcome.CARRIER_INELIGIBLE.value,
}

SENTIMENT_ALIASES = {
    "pos": CallSentiment.POSITIVE.value,
    "neg": CallSentiment.NEGATIVE.value,
    "mixed": CallSentiment.NEUTRAL.value,
}


def _canonicalize(value: str | Enum, aliases: dict[str, str], allowed: set[str]) -> str:
    if isinstance(value, Enum):
        normalized = str(value.value).strip().lower()
    else:
        normalized = str(value or "").strip().lower()

    canonical = aliases.get(normalized, normalized)
    if canonical not in allowed:
        raise ValueError(f"Unsupported value: {value}")
    return canonical


class CallCompleteRequest(BaseModel):
    external_call_id: str
    mc_number: str | None = None
    load_id: str | None = None
    final_rate: int | None = None
    outcome: CallOutcome
    sentiment: CallSentiment
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
        return int(float(v) + 0.5)

    @field_validator("outcome", mode="before")
    @classmethod
    def canonicalize_outcome(cls, v):
        allowed = {item.value for item in CallOutcome}
        return _canonicalize(v, OUTCOME_ALIASES, allowed)

    @field_validator("sentiment", mode="before")
    @classmethod
    def canonicalize_sentiment(cls, v):
        allowed = {item.value for item in CallSentiment}
        return _canonicalize(v, SENTIMENT_ALIASES, allowed)


class CallCompleteResponse(BaseModel):
    external_call_id: str
    status: str
    load_status: str | None = None
    completed_at: datetime
