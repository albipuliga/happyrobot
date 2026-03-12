from pydantic import BaseModel


class MetricsSummaryResponse(BaseModel):
    total_calls: int
    verified_calls: int
    verification_pass_rate: float
    matched_calls: int
    agreements: int
    transfers_ready: int
    outcome_counts: dict[str, int]
    sentiment_counts: dict[str, int]
    average_agreed_vs_listed_delta: float | None = None
    total_agreed_vs_listed_delta: int
