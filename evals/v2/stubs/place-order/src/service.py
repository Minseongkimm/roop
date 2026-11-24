"""Trivial stub: deducts stock line by line with no rollback, cancel is a no-op."""

from __future__ import annotations

from src.models import Item, Order, OrderLine
from src.store import Store


class InventoryService:
    def __init__(self, store: Store | None = None) -> None:
        self.store: Store = store or Store()
        self._orders: list[Order] = []

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
            if key in data:
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
        return self.update_item(item_id, quantity=item.quantity + delta)

    def place_order(self, lines: list[dict[str, object]]) -> Order:
        # Deduct immediately; if a later line fails, earlier deductions stay.
        built: list[OrderLine] = []
        for raw in lines:
            item: Item = self.get_item(int(raw["item_id"]))  # type: ignore[arg-type]
            quantity: int = int(raw["quantity"])  # type: ignore[arg-type]
            self.update_item(item.id, quantity=item.quantity - quantity)
            built.append(
                OrderLine(
                    item_id=item.id,
                    quantity=quantity,
                    unit_price_cents=item.price_cents,
                )
            )
        order: Order = Order(
            id=len(self._orders) + 1,
            lines=tuple(built),
            status="placed",
            total_cents=0,
        )
        self._orders.append(order)
        return order

    def get_order(self, order_id: int) -> Order:
        for order in self._orders:
            if order.id == order_id:
                return order
        raise KeyError(order_id)

    def list_orders(self) -> list[Order]:
        return list(self._orders)

    def cancel_order(self, order_id: int) -> Order:
        return self.get_order(order_id)
