from pydantic import BaseModel, Field


class NegotiateRequest(BaseModel):
    external_call_id: str
    load_id: str
    carrier_offer: int = Field(gt=0)


class NegotiateResponse(BaseModel):
    decision: str
    broker_offer: int | None = None
    round: int
    attempts_remaining: int
    transfer_ready: bool
    summary_for_agent: str
