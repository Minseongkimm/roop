"""In-memory item and category storage."""

from __future__ import annotations

from src.models import Category, Item


class Store:
    def __init__(self) -> None:
        self._items: dict[int, Item] = {}
        self._categories: dict[int, Category] = {}
        self._next_id: int = 1
        self._next_category_id: int = 1

    def create_item(
        self,
        sku: str,
        name: str,
        quantity: int,
        price_cents: int,
        category_id: int | None = None,
    ) -> Item:
        item: Item = Item(
            id=self._next_id,
            sku=sku,
            name=name,
            quantity=quantity,
            price_cents=price_cents,
            category_id=category_id,
        )
        self._items[item.id] = item
        self._next_id += 1
        return item

    def get_item(self, item_id: int) -> Item | None:
        return self._items.get(item_id)

    def get_item_by_sku(self, sku: str) -> Item | None:
        for item in self._items.values():
            if item.sku == sku:
                return item
        return None

    def list_items(self) -> list[Item]:
        return [self._items[key] for key in sorted(self._items)]

    def save_item(self, item: Item) -> Item:
        if item.id not in self._items:
            raise KeyError(item.id)
        self._items[item.id] = item
        return item

    def delete_item(self, item_id: int) -> bool:
        if item_id not in self._items:
            return False
        del self._items[item_id]
        return True

    def create_category(self, name: str, slug: str) -> Category:
        category: Category = Category(
            id=self._next_category_id, name=name, slug=slug
        )
        self._categories[category.id] = category
        self._next_category_id += 1
        return category

    def get_category(self, category_id: int) -> Category | None:
        return self._categories.get(category_id)

    def get_category_by_slug(self, slug: str) -> Category | None:
        for category in self._categories.values():
            if category.slug == slug:
                return category
        return None

    def list_categories(self) -> list[Category]:
        return [self._categories[key] for key in sorted(self._categories)]

    def save_category(self, category: Category) -> Category:
        if category.id not in self._categories:
            raise KeyError(category.id)
        self._categories[category.id] = category
        return category

    def delete_category(self, category_id: int) -> bool:
        if category_id not in self._categories:
            return False
        del self._categories[category_id]
        return True
