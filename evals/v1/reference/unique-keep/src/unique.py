def unique_keep(items: list[object]) -> list[object]:
    seen: set[object] = set()
    result: list[object] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result
