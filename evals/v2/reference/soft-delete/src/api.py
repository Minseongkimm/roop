"""Dict-in, dict-out handlers with soft delete and restore."""

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
        "deleted": item.deleted,
    }


def _truthy(value: object) -> bool:
    if value is True or value == 1:
        return True
    if isinstance(value, str) and value.strip().lower() in {"1", "true", "yes"}:
        return True
    return False


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
    params: dict[str, Any] = query or {}
    include_deleted: bool = _truthy(params.get("include_deleted", False))
    items: list[Item] = service.list_items(include_deleted=include_deleted)
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


def restore_item(service: InventoryService, item_id: int) -> dict[str, Any]:
    try:
        item: Item = service.restore_item(item_id)
    except KeyError:
        return {"ok": False, "error": "not found"}
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "item": item_to_dict(item)}
