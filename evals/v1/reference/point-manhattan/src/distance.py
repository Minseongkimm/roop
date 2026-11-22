from src.point import Point


def manhattan(left: Point, right: Point) -> int:
    if not isinstance(left, Point) or not isinstance(right, Point):
        raise TypeError('expected Point')
    return abs(left.x - right.x) + abs(left.y - right.y)
