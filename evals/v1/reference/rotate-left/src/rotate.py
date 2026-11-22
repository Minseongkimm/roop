def rotate_left(items: list[object], steps: int) -> list[object]:
    if isinstance(steps, bool) or not isinstance(steps, int):
        raise ValueError('steps must be an int')
    copied: list[object] = list(items)
    if not copied:
        return []
    shift: int = steps % len(copied)
    return copied[shift:] + copied[:shift]
