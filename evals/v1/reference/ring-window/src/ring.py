class Ring:
    def __init__(self, capacity: int) -> None:
        if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity < 1:
            raise ValueError('capacity must be >= 1')
        self._capacity: int = capacity
        self._items: list[object] = []

    def push(self, item: object) -> None:
        self._items.append(item)
        if len(self._items) > self._capacity:
            self._items.pop(0)

    def items(self) -> list[object]:
        return list(self._items)

    def size(self) -> int:
        return len(self._items)
