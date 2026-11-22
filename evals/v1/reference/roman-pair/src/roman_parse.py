_TOKENS: tuple[tuple[str, int], ...] = (
    ('M', 1000), ('CM', 900), ('D', 500), ('CD', 400),
    ('C', 100), ('XC', 90), ('L', 50), ('XL', 40),
    ('X', 10), ('IX', 9), ('V', 5), ('IV', 4), ('I', 1),
)


def _canonical(value: int) -> str:
    rest: int = value
    parts: list[str] = []
    for glyph, number in _TOKENS:
        while rest >= number:
            parts.append(glyph)
            rest -= number
    return ''.join(parts)


def parse_roman(text: str) -> int:
    if not isinstance(text, str) or not text or text != text.upper():
        raise ValueError('invalid roman')
    rest: str = text
    total: int = 0
    while rest:
        matched: bool = False
        for glyph, number in _TOKENS:
            if rest.startswith(glyph):
                total += number
                rest = rest[len(glyph):]
                matched = True
                break
        if not matched:
            raise ValueError('invalid roman')
    if not 1 <= total <= 3999 or _canonical(total) != text:
        raise ValueError('invalid roman')
    return total
