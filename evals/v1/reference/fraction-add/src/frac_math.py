from src.fraction import reduce_fraction


def add_fractions(
    left: tuple[int, int], right: tuple[int, int]
) -> tuple[int, int]:
    left_num, left_den = left
    right_num, right_den = right
    return reduce_fraction(
        left_num * right_den + right_num * left_den,
        left_den * right_den,
    )
