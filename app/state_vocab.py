from collections.abc import Collection
from enum import Enum


UNKNOWN_LABEL = "unknown"


class LoadStatus(str, Enum):
    AVAILABLE = "available"
    PENDING_TRANSFER = "pending_transfer"


class CallOutcome(str, Enum):
    BOOKED = "booked"
    NO_MATCH = "no_match"
    REJECTED_RATE = "rejected_rate"
    CARRIER_INELIGIBLE = "carrier_ineligible"
    OTHER = "other"


class CallSentiment(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class NegotiationDecision(str, Enum):
    ACCEPTED = "accepted"
    COUNTERED = "countered"
    REJECTED = "rejected"


LOAD_STATUS_VALUES = frozenset(item.value for item in LoadStatus)
CALL_OUTCOME_VALUES = frozenset(item.value for item in CallOutcome)
CALL_SENTIMENT_VALUES = frozenset(item.value for item in CallSentiment)
NEGOTIATION_DECISION_VALUES = frozenset(item.value for item in NegotiationDecision)


def _normalize_raw(value: str | None) -> str | None:
    normalized = str(value or "").strip().lower()
    return normalized or None


def normalize_reporting_value(value: str | None, allowed_values: Collection[str]) -> str:
    normalized = _normalize_raw(value)
    if normalized in allowed_values:
        return normalized
    return UNKNOWN_LABEL


def normalize_load_status_for_reporting(value: str | None) -> str:
    return normalize_reporting_value(value, LOAD_STATUS_VALUES)


def normalize_call_outcome_for_reporting(value: str | None) -> str:
    return normalize_reporting_value(value, CALL_OUTCOME_VALUES)


def normalize_call_sentiment_for_reporting(value: str | None) -> str:
    return normalize_reporting_value(value, CALL_SENTIMENT_VALUES)
