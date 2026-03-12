from datetime import date

from sqlalchemy.orm import Session

from app.models.call_session import CallSession
from app.models.load import Load
from app.schemas.loads import LoadSearchRequest, LoadSearchResponse, LoadSummary
from app.services.calls import get_or_create_call_session


def _normalize_text(value: str | None) -> str:
    return (value or "").strip().lower()


def _lane_score(load: Load, origin: str | None, destination: str | None) -> int:
    score = 0
    normalized_origin = _normalize_text(origin)
    normalized_destination = _normalize_text(destination)

    if normalized_origin and normalized_origin in load.origin.lower():
        score += 2
    if normalized_destination and normalized_destination in load.destination.lower():
        score += 2
    return score


def _pickup_distance(load: Load, pickup_date: date | None) -> int:
    if pickup_date is None:
        return 0
    return abs((load.pickup_datetime.date() - pickup_date).days)


def _to_summary(load: Load) -> LoadSummary:
    return LoadSummary(
        load_id=load.load_id,
        origin=load.origin,
        destination=load.destination,
        pickup_datetime=load.pickup_datetime,
        delivery_datetime=load.delivery_datetime,
        equipment_type=load.equipment_type,
        loadboard_rate=load.loadboard_rate,
        notes=load.notes,
        weight=load.weight,
        commodity_type=load.commodity_type,
        num_of_pieces=load.num_of_pieces,
        miles=load.miles,
        dimensions=load.dimensions,
        status=load.status,
    )


def search_loads(db: Session, payload: LoadSearchRequest) -> LoadSearchResponse:
    equipment = _normalize_text(payload.equipment_type)
    call_session = get_or_create_call_session(db=db, external_call_id=payload.external_call_id)

    candidate_loads = (
        db.query(Load)
        .filter(Load.status == "available")
        .filter(Load.equipment_type.ilike(payload.equipment_type))
        .all()
    )

    ranked_loads = sorted(
        candidate_loads,
        key=lambda load: (-_lane_score(load, payload.origin, payload.destination), _pickup_distance(load, payload.pickup_date), load.pickup_datetime),
    )

    top_matches = ranked_loads[:3]
    call_session.matched_loads_count = len(top_matches)
    if top_matches:
        call_session.selected_load_id = top_matches[0].id
    db.add(call_session)
    db.commit()

    summaries = [_to_summary(load) for load in top_matches]
    best_match = summaries[0] if summaries else None
    if best_match:
        summary = (
            f"Found {len(summaries)} matching loads. Lead with load {best_match.load_id} "
            f"from {best_match.origin} to {best_match.destination} at ${best_match.loadboard_rate}."
        )
    else:
        summary = f"No {equipment} loads are available for the requested lane right now."

    return LoadSearchResponse(matches=summaries, best_match=best_match, summary_for_agent=summary)
