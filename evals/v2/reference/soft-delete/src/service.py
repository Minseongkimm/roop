"""Business operations with soft delete and restore."""

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

    def get_item(self, item_id: int, include_deleted: bool = False) -> Item:
        item: Item | None = self.store.get_item(item_id)
        if item is None:
            raise KeyError(item_id)
        if item.deleted and not include_deleted:
            raise KeyError(item_id)
        return item

    def list_items(self, include_deleted: bool = False) -> list[Item]:
        return self.store.list_items(include_deleted=include_deleted)

    def update_item(self, item_id: int, **fields: object) -> Item:
        item: Item = self.get_item(item_id)
        data: dict[str, object] = {
            "id": item.id,
            "sku": item.sku,
            "name": item.name,
            "quantity": item.quantity,
            "price_cents": item.price_cents,
            "deleted": item.deleted,
        }
        for key, value in fields.items():
            if key not in {"sku", "name", "quantity", "price_cents"}:
                raise ValueError(f"unknown field: {key}")
            data[key] = value
        updated: Item = Item(
            id=item.id,
            sku=str(data["sku"]),
            name=str(data["name"]),
            quantity=int(data["quantity"]),  # type: ignore[arg-type]
            price_cents=int(data["price_cents"]),  # type: ignore[arg-type]
            deleted=bool(data["deleted"]),
        )
        return self.store.save_item(updated)

    def delete_item(self, item_id: int) -> None:
        self.get_item(item_id)
        if not self.store.delete_item(item_id):
            raise KeyError(item_id)

    def restore_item(self, item_id: int) -> Item:
        item: Item = self.get_item(item_id, include_deleted=True)
        if not item.deleted:
            raise ValueError("item is not deleted")
        restored: Item = Item(
            id=item.id,
            sku=item.sku,
            name=item.name,
            quantity=item.quantity,
            price_cents=item.price_cents,
            deleted=False,
        )
        return self.store.save_item(restored)

    def adjust_stock(self, item_id: int, delta: int) -> Item:
        item: Item = self.get_item(item_id)
        new_qty: int = item.quantity + delta
        if new_qty < 0:
            raise ValueError("insufficient stock")
        return self.update_item(item_id, quantity=new_qty)
