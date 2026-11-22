def transpose(rows: list[list[int]]) -> list[list[int]]:
    if not rows:
        return []
    width: int = len(rows[0])
    if any(len(row) != width for row in rows):
        raise ValueError('ragged matrix')
    copied: list[list[int]] = [list(row) for row in rows]
    return [list(column) for column in zip(*copied)]
