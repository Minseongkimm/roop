"""Business operations, including paged item lists."""

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
        if isinstance(page, bool) or not isinstance(page, int) or page < 1:
            raise ValueError("invalid page")
        if isinstance(page_size, bool) or not isinstance(page_size, int):
            raise ValueError("invalid page_size")
        if page_size < 1 or page_size > 100:
            raise ValueError("invalid page_size")
        items: list[Item] = self.list_items()
        total: int = len(items)
        start: int = (page - 1) * page_size
        return items[start : start + page_size], total

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
        updated: Item = Item(
            id=item.id,
            sku=str(data["sku"]),
            name=str(data["name"]),
            quantity=int(data["quantity"]),  # type: ignore[arg-type]
            price_cents=int(data["price_cents"]),  # type: ignore[arg-type]
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
