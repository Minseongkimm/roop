from src.temp_parse import parse_temp


def convert_temp(text: str, unit: str) -> str:
    value, source = parse_temp(text)
    target: str = unit.strip().upper()
    if target not in {'C', 'F'}:
        raise ValueError('invalid unit')
    if source == 'F' and target == 'C':
        converted: float = (value - 32) * 5 / 9
    elif source == 'C' and target == 'F':
        converted = value * 9 / 5 + 32
    else:
        converted = value
    return f'{converted:.1f}{target}'
