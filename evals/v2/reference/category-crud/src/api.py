"""Dict-in, dict-out handlers for items and categories."""

from __future__ import annotations

from typing import Any

from src.models import Category, Item
from src.service import InventoryService


def item_to_dict(item: Item) -> dict[str, Any]:
    return {
        "id": item.id,
        "sku": item.sku,
        "name": item.name,
        "quantity": item.quantity,
        "price_cents": item.price_cents,
        "category_id": item.category_id,
    }


def category_to_dict(category: Category) -> dict[str, Any]:
    return {"id": category.id, "name": category.name, "slug": category.slug}


def create_item(service: InventoryService, body: dict[str, Any]) -> dict[str, Any]:
    try:
        item: Item = service.create_item(
            sku=body["sku"],
            name=body["name"],
            quantity=body["quantity"],
            price_cents=body["price_cents"],
            category_id=body.get("category_id"),
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


def create_category(service: InventoryService, body: dict[str, Any]) -> dict[str, Any]:
    try:
        category: Category = service.create_category(
            name=body["name"], slug=body.get("slug")
        )
    except (KeyError, TypeError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "category": category_to_dict(category)}


def get_category(service: InventoryService, category_id: int) -> dict[str, Any]:
    try:
        category: Category = service.get_category(category_id)
    except KeyError:
        return {"ok": False, "error": "not found"}
    return {"ok": True, "category": category_to_dict(category)}


def list_categories(service: InventoryService) -> dict[str, Any]:
    categories: list[Category] = service.list_categories()
    return {
        "ok": True,
        "categories": [category_to_dict(item) for item in categories],
    }


def update_category(
    service: InventoryService, category_id: int, body: dict[str, Any]
) -> dict[str, Any]:
    try:
        category: Category = service.update_category(category_id, **body)
    except KeyError:
        return {"ok": False, "error": "not found"}
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "category": category_to_dict(category)}


def delete_category(service: InventoryService, category_id: int) -> dict[str, Any]:
    try:
        service.delete_category(category_id)
    except KeyError:
        return {"ok": False, "error": "not found"}
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True}
