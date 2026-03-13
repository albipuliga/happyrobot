from collections.abc import Callable

from app.schemas.dashboard import DashboardBreakdownItem, Tone

POSITIVE: Tone = "positive"
NEGATIVE: Tone = "negative"
PENDING: Tone = "pending"

OUTCOME_TONES: dict[str, Tone] = {
    "booked": POSITIVE,
    "no_match": PENDING,
    "other": PENDING,
    "carrier_ineligible": NEGATIVE,
    "rejected_rate": NEGATIVE,
    "accepted": POSITIVE,
    "agreed": POSITIVE,
    "agreement_reached": POSITIVE,
    "transfer_ready": POSITIVE,
    "countered": PENDING,
    "pending": PENDING,
    "rejected": NEGATIVE,
    "failed": NEGATIVE,
}

SENTIMENT_TONES: dict[str, Tone] = {
    "positive": POSITIVE,
    "neutral": PENDING,
    "mixed": PENDING,
    "negative": NEGATIVE,
}

LOAD_STATUS_TONES: dict[str, Tone] = {
    "available": PENDING,
    "booked": POSITIVE,
    "covered": POSITIVE,
    "pending_transfer": POSITIVE,
    "cancelled": NEGATIVE,
    "expired": NEGATIVE,
    "failed": NEGATIVE,
}


def _normalize(value: str | None) -> str:
    return str(value or "").strip().lower()


def _tone_from_map(value: str | None, mapping: dict[str, Tone]) -> Tone:
    return mapping.get(_normalize(value), PENDING)


def verification_tone(value: bool | None) -> Tone:
    if value is True:
        return POSITIVE
    if value is False:
        return NEGATIVE
    return PENDING


def outcome_tone(value: str | None) -> Tone:
    return _tone_from_map(value, OUTCOME_TONES)


def sentiment_tone(value: str | None) -> Tone:
    return _tone_from_map(value, SENTIMENT_TONES)


def load_status_tone(value: str | None) -> Tone:
    return _tone_from_map(value, LOAD_STATUS_TONES)


def build_breakdown_items(
    counts: dict[str, int],
    tone_resolver: Callable[[str | None], Tone],
) -> list[DashboardBreakdownItem]:
    return [
        DashboardBreakdownItem(label=label, count=count, tone=tone_resolver(label))
        for label, count in counts.items()
    ]
