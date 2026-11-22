import math


def reduce_ratio(numerator: int, denominator: int) -> tuple[int, int]:
    if denominator == 0:
        raise ValueError('zero denominator')
    sign: int = -1 if (numerator < 0) ^ (denominator < 0) else 1
    if numerator == 0:
        return (0, 1)
    num: int = abs(numerator)
    den: int = abs(denominator)
    divisor: int = math.gcd(num, den)
    return (sign * (num // divisor), den // divisor)


def parse_ratio(text: str) -> tuple[int, int]:
    raw: str = text.strip()
    if '/' in raw:
        left, right = raw.split('/', 1)
    else:
        left, right = raw, '1'
    try:
        numerator: int = int(left)
        denominator: int = int(right)
    except ValueError as exc:
        raise ValueError('invalid ratio') from exc
    return reduce_ratio(numerator, denominator)
