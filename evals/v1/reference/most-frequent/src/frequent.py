def most_frequent(items: list[object]) -> object:
    if not items:
        raise ValueError('empty items')
    counts: dict[object, int] = {}
    first: dict[object, int] = {}
    for index, item in enumerate(items):
        counts[item] = counts.get(item, 0) + 1
        if item not in first:
            first[item] = index
    return min(counts, key=lambda item: (-counts[item], first[item]))
