"""Business operations on top of the item store, with input validation."""

from __future__ import annotations

import re

from src.models import Item
from src.store import Store

_SKU_RE: re.Pattern[str] = re.compile(r"^[A-Z0-9]+(?:-[A-Z0-9]+)*$")
_MAX_NAME: int = 80


def _require_sku(sku: object) -> str:
    if not isinstance(sku, str):
        raise ValueError("invalid sku")
    cleaned: str = sku.strip().upper()
    if not _SKU_RE.fullmatch(cleaned):
        raise ValueError("invalid sku")
    return cleaned


def _require_name(name: object) -> str:
    if not isinstance(name, str):
        raise ValueError("invalid name")
    cleaned: str = name.strip()
    if not cleaned or len(cleaned) > _MAX_NAME:
        raise ValueError("invalid name")
    return cleaned


def _require_non_negative_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"invalid {label}")
    return value


class InventoryService:
    def __init__(self, store: Store | None = None) -> None:
        self.store: Store = store or Store()

    def create_item(
        self, sku: str, name: str, quantity: int, price_cents: int
    ) -> Item:
        cleaned_sku: str = _require_sku(sku)
        cleaned_name: str = _require_name(name)
        qty: int = _require_non_negative_int(quantity, "quantity")
        price: int = _require_non_negative_int(price_cents, "price")
        if self.store.get_item_by_sku(cleaned_sku) is not None:
            raise ValueError("duplicate sku")
        return self.store.create_item(cleaned_sku, cleaned_name, qty, price)

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
        }
        for key, value in fields.items():
            if key not in {"sku", "name", "quantity", "price_cents"}:
                raise ValueError(f"unknown field: {key}")
            data[key] = value
        cleaned_sku: str = _require_sku(data["sku"])
        existing: Item | None = self.store.get_item_by_sku(cleaned_sku)
        if existing is not None and existing.id != item.id:
            raise ValueError("duplicate sku")
        updated: Item = Item(
            id=item.id,
            sku=cleaned_sku,
            name=_require_name(data["name"]),
            quantity=_require_non_negative_int(data["quantity"], "quantity"),
            price_cents=_require_non_negative_int(data["price_cents"], "price"),
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
