def parse_temp(text: str) -> tuple[float, str]:
    raw: str = text.strip().replace(' ', '')
    if len(raw) < 2:
        raise ValueError('invalid temperature')
    unit: str = raw[-1].upper()
    if unit not in {'C', 'F'}:
        raise ValueError('invalid temperature')
    try:
        value: float = float(raw[:-1])
    except ValueError as exc:
        raise ValueError('invalid temperature') from exc
    return (value, unit)
