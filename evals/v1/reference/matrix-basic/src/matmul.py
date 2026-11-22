def _check(rows: list[list[int]]) -> int:
    if not rows or not rows[0]:
        raise ValueError('empty matrix')
    width: int = len(rows[0])
    if any(len(row) != width for row in rows):
        raise ValueError('ragged matrix')
    return width


def multiply(left: list[list[int]], right: list[list[int]]) -> list[list[int]]:
    left_width: int = _check(left)
    _check(right)
    if left_width != len(right):
        raise ValueError('incompatible shapes')
    result: list[list[int]] = []
    for row in left:
        result.append([
            sum(row[index] * right[index][column] for index in range(left_width))
            for column in range(len(right[0]))
        ])
    return result
