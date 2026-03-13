from collections import defaultdict
from collections.abc import Callable


def group_counts(
    rows: list[tuple[str | None, int]],
    normalizer: Callable[[str | None], str] | None = None,
) -> dict[str, int]:
    grouped: dict[str, int] = defaultdict(int)
    for label, count in rows:
        normalized_label = normalizer(label) if normalizer is not None else (label or "unknown")
        grouped[normalized_label] += count
    return dict(grouped)
