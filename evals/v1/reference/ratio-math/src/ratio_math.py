from src.ratio import parse_ratio, reduce_ratio


def multiply_ratios(left: str, right: str) -> tuple[int, int]:
    left_num, left_den = parse_ratio(left)
    right_num, right_den = parse_ratio(right)
    return reduce_ratio(left_num * right_num, left_den * right_den)
