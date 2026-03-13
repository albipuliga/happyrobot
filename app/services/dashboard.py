from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.call_session import CallSession
from app.models.load import Load
from app.models.negotiation_event import NegotiationEvent
from app.schemas.dashboard import DashboardDataResponse, DashboardLoadSnapshot, DashboardRecentCall
from app.services.common import group_counts
from app.services.metrics import build_metrics_summary


def build_dashboard_data(db: Session, limit: int = 25, offset: int = 0) -> DashboardDataResponse:
    summary = build_metrics_summary(db=db)

    load_status_counts = group_counts(db.query(Load.status, func.count(Load.id)).group_by(Load.status).all())

    total_calls = db.query(func.count(CallSession.id)).scalar() or 0

    negotiation_rounds_subquery = (
        db.query(
            NegotiationEvent.call_session_id.label("call_session_id"),
            func.count(NegotiationEvent.id).label("negotiation_rounds"),
        )
        .group_by(NegotiationEvent.call_session_id)
        .subquery()
    )

    recent_call_rows = (
        db.query(
            CallSession,
            Load,
            func.coalesce(negotiation_rounds_subquery.c.negotiation_rounds, 0),
        )
        .outerjoin(Load, CallSession.selected_load_id == Load.id)
        .outerjoin(negotiation_rounds_subquery, CallSession.id == negotiation_rounds_subquery.c.call_session_id)
        .order_by(CallSession.updated_at.desc(), CallSession.id.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    recent_calls = [
        DashboardRecentCall(
            external_call_id=call_session.external_call_id,
            started_at=call_session.started_at,
            ended_at=call_session.ended_at,
            mc_number=call_session.mc_number,
            verification_passed=call_session.verification_passed,
            matched_loads_count=call_session.matched_loads_count,
            outcome=call_session.outcome,
            sentiment=call_session.sentiment,
            agreed_rate=call_session.agreed_rate,
            selected_load=(
                DashboardLoadSnapshot(
                    load_id=load.load_id,
                    origin=load.origin,
                    destination=load.destination,
                    equipment_type=load.equipment_type,
                    loadboard_rate=load.loadboard_rate,
                    status=load.status,
                )
                if load is not None
                else None
            ),
            negotiation_rounds=int(negotiation_rounds or 0),
            transcript_excerpt=call_session.transcript_excerpt,
        )
        for call_session, load, negotiation_rounds in recent_call_rows
    ]

    return DashboardDataResponse(
        summary=summary,
        load_status_counts=load_status_counts,
        recent_calls=recent_calls,
        total_calls=total_calls,
        page_size=limit,
        last_updated_at=datetime.utcnow(),
    )
