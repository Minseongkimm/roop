import math


def reduce_fraction(numerator: int, denominator: int) -> tuple[int, int]:
    if (
        isinstance(numerator, bool)
        or isinstance(denominator, bool)
        or not isinstance(numerator, int)
        or not isinstance(denominator, int)
        or denominator == 0
    ):
        raise ValueError('invalid fraction')
    sign: int = -1 if (numerator < 0) ^ (denominator < 0) else 1
    num: int = abs(numerator)
    den: int = abs(denominator)
    if num == 0:
        return (0, 1)
    divisor: int = math.gcd(num, den)
    return (sign * (num // divisor), den // divisor)
