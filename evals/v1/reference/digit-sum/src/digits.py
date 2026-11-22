def digit_sum(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError('value must be a non-negative int')
    return sum(int(char) for char in str(value))
