"""Dict-in, dict-out handlers, including order placement."""

from __future__ import annotations

from typing import Any

from src.models import Item, Order
from src.service import InventoryService


def item_to_dict(item: Item) -> dict[str, Any]:
    return {
        "id": item.id,
        "sku": item.sku,
        "name": item.name,
        "quantity": item.quantity,
        "price_cents": item.price_cents,
    }


def order_to_dict(order: Order) -> dict[str, Any]:
    return {
        "id": order.id,
        "status": order.status,
        "total_cents": order.total_cents,
        "lines": [
            {
                "item_id": line.item_id,
                "quantity": line.quantity,
                "unit_price_cents": line.unit_price_cents,
            }
            for line in order.lines
        ],
    }


def create_item(service: InventoryService, body: dict[str, Any]) -> dict[str, Any]:
    try:
        item: Item = service.create_item(
            sku=body["sku"],
            name=body["name"],
            quantity=body["quantity"],
            price_cents=body["price_cents"],
        )
    except (KeyError, TypeError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "item": item_to_dict(item)}


def get_item(service: InventoryService, item_id: int) -> dict[str, Any]:
    try:
        item: Item = service.get_item(item_id)
    except KeyError:
        return {"ok": False, "error": "not found"}
    return {"ok": True, "item": item_to_dict(item)}


def list_items(
    service: InventoryService, query: dict[str, Any] | None = None
) -> dict[str, Any]:
    del query
    items: list[Item] = service.list_items()
    return {"ok": True, "items": [item_to_dict(item) for item in items]}


def update_item(
    service: InventoryService, item_id: int, body: dict[str, Any]
) -> dict[str, Any]:
    try:
        item: Item = service.update_item(item_id, **body)
    except KeyError:
        return {"ok": False, "error": "not found"}
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "item": item_to_dict(item)}


def delete_item(service: InventoryService, item_id: int) -> dict[str, Any]:
    try:
        service.delete_item(item_id)
    except KeyError:
        return {"ok": False, "error": "not found"}
    return {"ok": True}


def place_order(service: InventoryService, body: dict[str, Any]) -> dict[str, Any]:
    try:
        order: Order = service.place_order(list(body.get("lines") or []))
    except KeyError:
        return {"ok": False, "error": "not found"}
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "order": order_to_dict(order)}


def get_order(service: InventoryService, order_id: int) -> dict[str, Any]:
    try:
        order: Order = service.get_order(order_id)
    except KeyError:
        return {"ok": False, "error": "not found"}
    return {"ok": True, "order": order_to_dict(order)}


def list_orders(service: InventoryService) -> dict[str, Any]:
    return {
        "ok": True,
        "orders": [order_to_dict(order) for order in service.list_orders()],
    }


def cancel_order(service: InventoryService, order_id: int) -> dict[str, Any]:
    try:
        order: Order = service.cancel_order(order_id)
    except KeyError:
        return {"ok": False, "error": "not found"}
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "order": order_to_dict(order)}
