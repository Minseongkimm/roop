"""Business operations, including atomic order placement."""

from __future__ import annotations

from src.models import Item, Order, OrderLine
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

    def place_order(self, lines: list[dict[str, object]]) -> Order:
        parsed: list[OrderLine] = self._parse_lines(lines)
        # Validate stock first so a failure leaves quantities unchanged.
        reserved: list[tuple[Item, int]] = []
        for line in parsed:
            item: Item = self.get_item(line.item_id)
            if item.quantity < line.quantity:
                raise ValueError("insufficient stock")
            reserved.append((item, line.quantity))
        for item, quantity in reserved:
            self.update_item(item.id, quantity=item.quantity - quantity)
        total: int = sum(line.unit_price_cents * line.quantity for line in parsed)
        draft: Order = Order(
            id=0, lines=tuple(parsed), status="placed", total_cents=total
        )
        return self.store.create_order(draft)

    def get_order(self, order_id: int) -> Order:
        order: Order | None = self.store.get_order(order_id)
        if order is None:
            raise KeyError(order_id)
        return order

    def list_orders(self) -> list[Order]:
        return self.store.list_orders()

    def cancel_order(self, order_id: int) -> Order:
        order: Order = self.get_order(order_id)
        if order.status != "placed":
            raise ValueError("order is not cancellable")
        for line in order.lines:
            item: Item = self.get_item(line.item_id)
            self.update_item(item.id, quantity=item.quantity + line.quantity)
        cancelled: Order = Order(
            id=order.id,
            lines=order.lines,
            status="cancelled",
            total_cents=order.total_cents,
        )
        return self.store.save_order(cancelled)

    def _parse_lines(self, lines: list[dict[str, object]]) -> list[OrderLine]:
        if not isinstance(lines, list) or not lines:
            raise ValueError("invalid lines")
        seen: set[int] = set()
        parsed: list[OrderLine] = []
        for raw in lines:
            if not isinstance(raw, dict):
                raise ValueError("invalid lines")
            item_id = raw.get("item_id")
            quantity = raw.get("quantity")
            if isinstance(item_id, bool) or not isinstance(item_id, int):
                raise ValueError("invalid lines")
            if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
                raise ValueError("invalid lines")
            if item_id in seen:
                raise ValueError("duplicate item")
            seen.add(item_id)
            item: Item = self.get_item(item_id)
            parsed.append(
                OrderLine(
                    item_id=item.id,
                    quantity=quantity,
                    unit_price_cents=item.price_cents,
                )
            )
        return parsed
