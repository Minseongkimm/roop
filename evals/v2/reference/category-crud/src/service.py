"""Business operations including category CRUD."""

from __future__ import annotations

import re

from src.models import Category, Item
from src.store import Store

_SLUG_RE: re.Pattern[str] = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_MAX_CATEGORY_NAME: int = 40


def _slugify(name: str) -> str:
    compact: str = "-".join(name.strip().lower().split())
    return compact


def _require_category_name(name: object) -> str:
    if not isinstance(name, str):
        raise ValueError("invalid name")
    cleaned: str = name.strip()
    if not cleaned or len(cleaned) > _MAX_CATEGORY_NAME:
        raise ValueError("invalid name")
    return cleaned


def _require_slug(slug: object) -> str:
    if not isinstance(slug, str):
        raise ValueError("invalid slug")
    cleaned: str = slug.strip().lower()
    if not _SLUG_RE.fullmatch(cleaned):
        raise ValueError("invalid slug")
    return cleaned


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
        resolved: int | None = self._require_category_id(category_id)
        return self.store.create_item(sku, name, quantity, price_cents, resolved)

    def get_item(self, item_id: int) -> Item:
        item: Item | None = self.store.get_item(item_id)
        if item is None:
            raise KeyError(item_id)
        return item

    def list_items(self) -> list[Item]:
        return self.store.list_items()

    def update_item(self, item_id: int, **fields: object) -> Item:
        item: Item = self.get_item(item_id)
        data: dict[str, object] = {
            "id": item.id,
            "sku": item.sku,
            "name": item.name,
            "quantity": item.quantity,
            "price_cents": item.price_cents,
            "category_id": item.category_id,
        }
        allowed: set[str] = {
            "sku",
            "name",
            "quantity",
            "price_cents",
            "category_id",
        }
        for key, value in fields.items():
            if key not in allowed:
                raise ValueError(f"unknown field: {key}")
            data[key] = value
        category_id: int | None = self._require_category_id(data["category_id"])
        updated: Item = Item(
            id=item.id,
            sku=str(data["sku"]),
            name=str(data["name"]),
            quantity=int(data["quantity"]),  # type: ignore[arg-type]
            price_cents=int(data["price_cents"]),  # type: ignore[arg-type]
            category_id=category_id,
        )
        return self.store.save_item(updated)

    def delete_item(self, item_id: int) -> None:
        if not self.store.delete_item(item_id):
            raise KeyError(item_id)

    def adjust_stock(self, item_id: int, delta: int) -> Item:
        item: Item = self.get_item(item_id)
        new_qty: int = item.quantity + delta
        if new_qty < 0:
            raise ValueError("insufficient stock")
        return self.update_item(item_id, quantity=new_qty)

    def create_category(self, name: str, slug: str | None = None) -> Category:
        cleaned_name: str = _require_category_name(name)
        cleaned_slug: str = _require_slug(slug if slug is not None else _slugify(cleaned_name))
        if self.store.get_category_by_slug(cleaned_slug) is not None:
            raise ValueError("duplicate slug")
        return self.store.create_category(cleaned_name, cleaned_slug)

    def get_category(self, category_id: int) -> Category:
        category: Category | None = self.store.get_category(category_id)
        if category is None:
            raise KeyError(category_id)
        return category

    def list_categories(self) -> list[Category]:
        return self.store.list_categories()

    def update_category(self, category_id: int, **fields: object) -> Category:
        category: Category = self.get_category(category_id)
        name: str = category.name
        slug: str = category.slug
        for key, value in fields.items():
            if key == "name":
                name = _require_category_name(value)
            elif key == "slug":
                slug = _require_slug(value)
            else:
                raise ValueError(f"unknown field: {key}")
        existing: Category | None = self.store.get_category_by_slug(slug)
        if existing is not None and existing.id != category.id:
            raise ValueError("duplicate slug")
        return self.store.save_category(Category(id=category.id, name=name, slug=slug))

    def delete_category(self, category_id: int) -> None:
        self.get_category(category_id)
        for item in self.store.list_items():
            if item.category_id == category_id:
                raise ValueError("category in use")
        if not self.store.delete_category(category_id):
            raise KeyError(category_id)

    def _require_category_id(self, category_id: object) -> int | None:
        if category_id is None:
            return None
        if isinstance(category_id, bool) or not isinstance(category_id, int):
            raise ValueError("invalid category")
        self.get_category(category_id)
        return category_id
