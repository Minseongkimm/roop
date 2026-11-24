"""Trivial stub: category methods exist but always fail."""

from __future__ import annotations

from src.models import Category, Item
from src.store import Store


class InventoryService:
    def __init__(self, store: Store | None = None) -> None:
        self.store: Store = store or Store()

    def create_item(
        self,
        sku: str,
        name: str,
        quantity: int,
        price_cents: int,
        category_id: int | None = None,
    ) -> Item:
        del category_id
        return self.store.create_item(sku, name, quantity, price_cents)

    def get_item(self, item_id: int) -> Item:
        item: Item | None = self.store.get_item(item_id)
        if item is None:
            raise KeyError(item_id)
        return item

    def list_items(self) -> list[Item]:
        return self.store.list_items()

    def update_item(self, item_id: int, **fields: object) -> Item:
        raise ValueError("not implemented")

    def delete_item(self, item_id: int) -> None:
        if not self.store.delete_item(item_id):
            raise KeyError(item_id)

    def adjust_stock(self, item_id: int, delta: int) -> Item:
        raise ValueError("not implemented")

    def create_category(self, name: str, slug: str | None = None) -> Category:
        raise ValueError("not implemented")

    def get_category(self, category_id: int) -> Category:
        raise KeyError(category_id)

    def list_categories(self) -> list[Category]:
        return []

    def update_category(self, category_id: int, **fields: object) -> Category:
        raise ValueError("not implemented")

    def delete_category(self, category_id: int) -> None:
        raise KeyError(category_id)
