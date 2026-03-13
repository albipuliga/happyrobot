from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.call_session import CallSession
from app.models.load import Load
from app.schemas.metrics import MetricsSummaryResponse
from app.services.common import group_counts


def build_metrics_summary(db: Session) -> MetricsSummaryResponse:
    total_calls = db.query(func.count(CallSession.id)).scalar() or 0
    verified_calls = db.query(func.count(CallSession.id)).filter(CallSession.verification_passed.is_(True)).scalar() or 0
    matched_calls = db.query(func.count(CallSession.id)).filter(CallSession.matched_loads_count > 0).scalar() or 0
    agreements = db.query(func.count(CallSession.id)).filter(CallSession.outcome == "booked").scalar() or 0
    transfers_ready = db.query(func.count(Load.id)).filter(Load.status == "pending_transfer").scalar() or 0

    outcome_counts = group_counts(
        db.query(CallSession.outcome, func.count(CallSession.id)).group_by(CallSession.outcome).all()
    )
    sentiment_counts = group_counts(
        db.query(CallSession.sentiment, func.count(CallSession.id)).group_by(CallSession.sentiment).all()
    )

    agreed_delta_rows = (
        db.query(CallSession.agreed_rate, Load.loadboard_rate)
        .join(Load, CallSession.selected_load_id == Load.id)
        .filter(CallSession.agreed_rate.is_not(None))
        .all()
    )
    deltas = [agreed_rate - listed_rate for agreed_rate, listed_rate in agreed_delta_rows if agreed_rate is not None and listed_rate is not None]
    average_delta = round(sum(deltas) / len(deltas), 2) if deltas else None

    verification_pass_rate = round((verified_calls / total_calls) * 100, 2) if total_calls else 0.0

    return MetricsSummaryResponse(
        total_calls=total_calls,
        verified_calls=verified_calls,
        verification_pass_rate=verification_pass_rate,
        matched_calls=matched_calls,
        agreements=agreements,
        transfers_ready=transfers_ready,
        outcome_counts=outcome_counts,
        sentiment_counts=sentiment_counts,
        average_agreed_vs_listed_delta=average_delta,
        total_agreed_vs_listed_delta=sum(deltas),
    )
