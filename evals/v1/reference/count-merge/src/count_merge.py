from src.counts import parse_counts


def merge_counts(parts: list[str]) -> dict[str, int]:
    merged: dict[str, int] = {}
    for part in parts:
        for key, value in parse_counts(part).items():
            merged[key] = merged.get(key, 0) + value
    return merged
