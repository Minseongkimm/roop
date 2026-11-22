def running_max(items: list[int]) -> list[int]:
    result: list[int] = []
    best: int | None = None
    for item in items:
        if best is None or item > best:
            best = item
        assert best is not None
        result.append(best)
    return result
