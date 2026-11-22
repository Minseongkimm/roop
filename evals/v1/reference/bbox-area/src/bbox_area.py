from src.bbox import parse_point


def area(corners: list[str]) -> int:
    if not corners:
        raise ValueError('no corners')
    points: list[tuple[int, int]] = [parse_point(item) for item in corners]
    xs: list[int] = [point[0] for point in points]
    ys: list[int] = [point[1] for point in points]
    return (max(xs) - min(xs)) * (max(ys) - min(ys))
