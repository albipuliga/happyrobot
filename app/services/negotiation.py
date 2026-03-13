from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.load import Load
from app.models.negotiation_event import NegotiationEvent
from app.schemas.negotiation import NegotiateRequest, NegotiateResponse
from app.services.calls import get_or_create_call_session


def _round_to_nearest_25(value: float) -> int:
    return int(round(value / 25.0) * 25)


def _counter_offer(load: Load, round_number: int) -> int:
    gap = load.max_rate - load.loadboard_rate
    if round_number == 1:
        return _round_to_nearest_25(load.loadboard_rate + (gap * 0.5))
    if round_number == 2:
        return _round_to_nearest_25(load.loadboard_rate + (gap * 0.8))
    return load.max_rate


def negotiate_rate(db: Session, payload: NegotiateRequest) -> NegotiateResponse:
    settings = get_settings()
    max_counter_rounds = settings.negotiation_max_counter_rounds
    load = db.query(Load).filter(Load.load_id == payload.load_id).one_or_none()
    if load is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Load not found.")
    if load.status != "available":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Load is no longer open for negotiation.")

    call_session = get_or_create_call_session(db=db, external_call_id=payload.external_call_id)
    call_session.selected_load_id = load.id

    previous_events = (
        db.query(NegotiationEvent)
        .filter(NegotiationEvent.call_session_id == call_session.id, NegotiationEvent.load_id == load.id)
        .order_by(NegotiationEvent.round_number.asc(), NegotiationEvent.created_at.asc())
        .all()
    )
    rounds_completed = len(previous_events)
    current_allowed_rate = load.loadboard_rate if rounds_completed == 0 else _counter_offer(load, min(rounds_completed, max_counter_rounds))

    if payload.carrier_offer <= current_allowed_rate:
        accepted_round = rounds_completed if rounds_completed > 0 else 0
        event = NegotiationEvent(
            call_session_id=call_session.id,
            load_id=load.id,
            round_number=accepted_round,
            carrier_offer=payload.carrier_offer,
            broker_counter=payload.carrier_offer,
            decision="accepted",
        )
        call_session.agreed_rate = payload.carrier_offer
        db.add_all([call_session, event])
        db.commit()
        return NegotiateResponse(
            decision="accepted",
            broker_offer=payload.carrier_offer,
            round=accepted_round,
            attempts_remaining=max(0, max_counter_rounds - rounds_completed),
            transfer_ready=True,
            summary_for_agent=f"Accept the offer at ${payload.carrier_offer} and move to transfer.",
        )

    if rounds_completed >= max_counter_rounds:
        event = NegotiationEvent(
            call_session_id=call_session.id,
            load_id=load.id,
            round_number=max_counter_rounds,
            carrier_offer=payload.carrier_offer,
            broker_counter=load.max_rate,
            decision="rejected",
        )
        db.add_all([call_session, event])
        db.commit()
        return NegotiateResponse(
            decision="rejected",
            broker_offer=load.max_rate,
            round=max_counter_rounds,
            attempts_remaining=0,
            transfer_ready=False,
            summary_for_agent=f"Politely decline. The final approved rate was ${load.max_rate} and the carrier stayed above it.",
        )

    next_round = rounds_completed + 1
    counter = _counter_offer(load, next_round)
    event = NegotiationEvent(
        call_session_id=call_session.id,
        load_id=load.id,
        round_number=next_round,
        carrier_offer=payload.carrier_offer,
        broker_counter=counter,
        decision="countered",
    )
    db.add_all([call_session, event])
    db.commit()

    return NegotiateResponse(
        decision="countered",
        broker_offer=counter,
        round=next_round,
        attempts_remaining=max(0, max_counter_rounds - next_round),
        transfer_ready=False,
        summary_for_agent=f"Counter at ${counter}. This is round {next_round} of {max_counter_rounds}.",
    )
