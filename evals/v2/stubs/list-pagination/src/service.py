"""Trivial stub: paginate_items ignores page and returns every item."""

from __future__ import annotations

from src.models import Item
from src.store import Store


class InventoryService:
    def __init__(self, store: Store | None = None) -> None:
        self.store: Store = store or Store()

    def create_item(
        self, sku: str, name: str, quantity: int, price_cents: int
    ) -> Item:
        return self.store.create_item(sku, name, quantity, price_cents)

    def get_item(self, item_id: int) -> Item:
        item: Item | None = self.store.get_item(item_id)
        if item is None:
            raise KeyError(item_id)
        return item

    def list_items(self) -> list[Item]:
        return self.store.list_items()

    def paginate_items(self, page: int, page_size: int) -> tuple[list[Item], int]:
        del page, page_size
        items: list[Item] = self.list_items()
        return items, len(items)

    def update_item(self, item_id: int, **fields: object) -> Item:
        raise ValueError("unknown field")

    def delete_item(self, item_id: int) -> None:
        if not self.store.delete_item(item_id):
            raise KeyError(item_id)

    def adjust_stock(self, item_id: int, delta: int) -> Item:
        raise ValueError("insufficient stock")
