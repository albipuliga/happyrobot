from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.call_session import CallSession
from app.models.load import Load
from app.schemas.calls import CallCompleteRequest, CallCompleteResponse, CallOutcome
from app.state_vocab import LoadStatus


def get_or_create_call_session(db: Session, external_call_id: str) -> CallSession:
    call_session = db.query(CallSession).filter(CallSession.external_call_id == external_call_id).one_or_none()
    if call_session is None:
        call_session = CallSession(external_call_id=external_call_id)
        db.add(call_session)
        db.flush()
    return call_session


def complete_call(db: Session, payload: CallCompleteRequest) -> CallCompleteResponse:
    call_session = get_or_create_call_session(db=db, external_call_id=payload.external_call_id)
    call_session.mc_number = payload.mc_number
    call_session.outcome = payload.outcome.value
    call_session.sentiment = payload.sentiment.value
    call_session.transcript_excerpt = payload.transcript_excerpt
    call_session.extracted_fields = payload.extracted_fields
    call_session.ended_at = datetime.utcnow()

    is_booked = payload.outcome == CallOutcome.BOOKED
    load_status = None
    if payload.load_id:
        load = db.query(Load).filter(Load.load_id == payload.load_id).one_or_none()
        if load is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Load not found.")

        call_session.selected_load = load
        load_status = load.status
        if is_booked:
            load.status = LoadStatus.PENDING_TRANSFER.value
            load_status = load.status

    if is_booked and payload.final_rate is not None:
        call_session.agreed_rate = payload.final_rate
    elif not is_booked:
        call_session.agreed_rate = None

    db.add(call_session)
    db.commit()
    db.refresh(call_session)

    return CallCompleteResponse(
        external_call_id=call_session.external_call_id,
        status="completed",
        load_status=load_status,
        completed_at=call_session.ended_at or datetime.utcnow(),
    )
