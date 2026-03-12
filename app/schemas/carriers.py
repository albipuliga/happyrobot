from pydantic import BaseModel, Field, field_validator


class VerifyCarrierRequest(BaseModel):
    external_call_id: str
    mc_number: str = Field(min_length=1)
    
    @field_validator("mc_number", mode="before")
    @classmethod
    def coerce_mc_number(cls, v):
        return str(v)


class VerifyCarrierResponse(BaseModel):
    verified: bool
    eligible: bool
    carrier_name: str | None = None
    dot_number: str | None = None
    authority_status: str | None = None
    reasons: list[str]
    summary_for_agent: str
