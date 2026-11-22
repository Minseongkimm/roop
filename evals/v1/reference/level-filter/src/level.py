_LEVELS: dict[str, int] = {'debug': 10, 'info': 20, 'warn': 30, 'error': 40}


def parse_level(name: str) -> int:
    key: str = name.strip().lower()
    if key not in _LEVELS:
        raise ValueError('unknown level')
    return _LEVELS[key]
