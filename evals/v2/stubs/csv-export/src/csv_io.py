"""Trivial stub: export is a header only; import always returns an empty list."""

from __future__ import annotations

from src.models import Item


def export_csv(items: list[Item]) -> str:
    del items
    return "sku,name,quantity,price_cents\n"


def import_csv(text: str) -> list[dict[str, object]]:
    del text
    return []
