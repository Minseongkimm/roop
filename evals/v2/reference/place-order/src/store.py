"""In-memory item and order storage."""

from __future__ import annotations

from src.models import Item, Order


class Store:
    def __init__(self) -> None:
        self._items: dict[int, Item] = {}
        self._orders: dict[int, Order] = {}
        self._next_id: int = 1
        self._next_order_id: int = 1

    def create_item(
        self, sku: str, name: str, quantity: int, price_cents: int
    ) -> Item:
        item: Item = Item(
            id=self._next_id,
            sku=sku,
            name=name,
            quantity=quantity,
            price_cents=price_cents,
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

    def create_order(self, order: Order) -> Order:
        saved: Order = Order(
            id=self._next_order_id,
            lines=order.lines,
            status=order.status,
            total_cents=order.total_cents,
        )
        self._orders[saved.id] = saved
        self._next_order_id += 1
        return saved

    def get_order(self, order_id: int) -> Order | None:
        return self._orders.get(order_id)

    def list_orders(self) -> list[Order]:
        return [self._orders[key] for key in sorted(self._orders)]

    def save_order(self, order: Order) -> Order:
        if order.id not in self._orders:
            raise KeyError(order.id)
        self._orders[order.id] = order
        return order
