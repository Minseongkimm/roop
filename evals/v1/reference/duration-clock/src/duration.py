def parse_duration(text: str) -> int:
    raw: str = text.strip()
    if not raw:
        raise ValueError('empty duration')
    if raw.isdigit():
        return int(raw)
    total: int = 0
    number: str = ''
    saw_unit: bool = False
    for char in raw:
        if char.isdigit():
            number += char
            continue
        if char in 'hm' and number:
            total += int(number) * (60 if char == 'h' else 1)
            number = ''
            saw_unit = True
            continue
        raise ValueError('invalid duration')
    if number or not saw_unit:
        raise ValueError('invalid duration')
    return total
