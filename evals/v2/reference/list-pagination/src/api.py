"""Dict-in, dict-out handlers with a paged list endpoint."""

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
    page: object = params.get("page", 1)
    page_size: object = params.get("page_size", 20)
    try:
        page_int: int = _as_int(page, "page")
        size_int: int = _as_int(page_size, "page_size")
        items, total = service.paginate_items(page_int, size_int)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    total_pages: int = 0 if total == 0 else (total + size_int - 1) // size_int
    return {
        "ok": True,
        "items": [item_to_dict(item) for item in items],
        "page": page_int,
        "page_size": size_int,
        "total": total,
        "total_pages": total_pages,
    }


def _as_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"invalid {label}")
    return value


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
