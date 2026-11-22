from src.ring import Ring


def last_n(ring: Ring, n: int) -> list[object]:
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        raise ValueError('n must be >= 1')
    return ring.items()[-n:]
