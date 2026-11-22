def zip_strict(left: list[object], right: list[object]) -> list[tuple[object, object]]:
    if len(left) != len(right):
        raise ValueError('lengths differ')
    return list(zip(left, right))
