from pydantic import BaseModel, Field, field_validator

from app.state_vocab import NegotiationDecision


class NegotiateRequest(BaseModel):
    external_call_id: str
    load_id: str
    carrier_offer: int = Field(gt=0)

    @field_validator("carrier_offer", mode="before")
    @classmethod
    def round_carrier_offer(cls, value):
        return int(float(value) + 0.5)


class NegotiateResponse(BaseModel):
    decision: NegotiationDecision
    broker_offer: int | None = None
    round: int
    attempts_remaining: int
    transfer_ready: bool
    summary_for_agent: str
