from collections import defaultdict


def group_counts(rows: list[tuple[str | None, int]]) -> dict[str, int]:
    grouped: dict[str, int] = defaultdict(int)
    for label, count in rows:
        grouped[label or "unknown"] += count
    return dict(grouped)
