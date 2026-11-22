def parse_span(text: str) -> tuple[int, int]:
    raw: str = text.strip()
    if '-' in raw:
        left, right = raw.split('-', 1)
        if not left.isdigit() or not right.isdigit():
            raise ValueError('invalid span')
        start, end = int(left), int(right)
    else:
        if not raw.isdigit():
            raise ValueError('invalid span')
        start = end = int(raw)
    if start > end:
        raise ValueError('invalid span')
    return (start, end)
