"""Trivial stub: list_items always returns every item with fake page metadata."""

from __future__ import annotations

from typing import Any

from src.models import Item
from src.service import InventoryService


def item_to_dict(item: Item) -> dict[str, Any]:
    return {
        "id": item.id,
        "sku": item.sku,
        "name": item.name,
        "quantity": item.quantity,
        "price_cents": item.price_cents,
    }


def create_item(service: InventoryService, body: dict[str, Any]) -> dict[str, Any]:
    item: Item = service.create_item(
        sku=body["sku"],
        name=body["name"],
        quantity=body["quantity"],
        price_cents=body["price_cents"],
    )
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
    return {
        "ok": True,
        "items": [item_to_dict(item) for item in items],
        "page": 1,
        "page_size": 20,
        "total": len(items),
        "total_pages": 1,
    }


def update_item(
    service: InventoryService, item_id: int, body: dict[str, Any]
) -> dict[str, Any]:
    del service, item_id, body
    return {"ok": False, "error": "not found"}


def delete_item(service: InventoryService, item_id: int) -> dict[str, Any]:
    del service, item_id
    return {"ok": False, "error": "not found"}
