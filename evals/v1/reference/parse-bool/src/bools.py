_TRUE: frozenset[str] = frozenset({'true', 'yes', '1'})
_FALSE: frozenset[str] = frozenset({'false', 'no', '0'})


def parse_bool(text: str) -> bool:
    key: str = text.strip().lower()
    if key in _TRUE:
        return True
    if key in _FALSE:
        return False
    raise ValueError('invalid boolean')
