class Point:
    def __init__(self, x: int, y: int) -> None:
        if isinstance(x, bool) or isinstance(y, bool) or not isinstance(x, int) or not isinstance(y, int):
            raise TypeError('coordinates must be ints')
        self.x: int = x
        self.y: int = y
