from src.sku import normalize_sku


class Inventory:
    def __init__(self) -> None:
        self._counts: dict[str, int] = {}

    def add(self, sku: str, qty: int) -> None:
        self._require_qty(qty)
        key: str = normalize_sku(sku)
        self._counts[key] = self._counts.get(key, 0) + qty

    def remove(self, sku: str, qty: int) -> None:
        self._require_qty(qty)
        key: str = normalize_sku(sku)
        current: int = self._counts.get(key, 0)
        if qty > current:
            raise ValueError('insufficient stock')
        self._counts[key] = current - qty

    def count(self, sku: str) -> int:
        return self._counts.get(normalize_sku(sku), 0)

    def _require_qty(self, qty: int) -> None:
        if isinstance(qty, bool) or not isinstance(qty, int) or qty < 1:
            raise ValueError('invalid quantity')
