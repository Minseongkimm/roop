from src.prefix_norm import normalize_key


class PrefixTable:
    def __init__(self) -> None:
        self._items: dict[str, object] = {}

    def add(self, key: str, value: object) -> None:
        self._items[normalize_key(key)] = value

    def get(self, key: str) -> object:
        normalized: str = normalize_key(key)
        if normalized not in self._items:
            raise KeyError(normalized)
        return self._items[normalized]
