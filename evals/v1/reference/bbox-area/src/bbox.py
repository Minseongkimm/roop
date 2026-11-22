def parse_point(text: str) -> tuple[int, int]:
    if ',' not in text:
        raise ValueError('invalid point')
    left, right = text.split(',', 1)
    left = left.strip()
    right = right.strip()
    if not _is_int(left) or not _is_int(right):
        raise ValueError('invalid point')
    return (int(left), int(right))


def _is_int(text: str) -> bool:
    if text.startswith('-'):
        text = text[1:]
    return bool(text) and text.isdigit()
