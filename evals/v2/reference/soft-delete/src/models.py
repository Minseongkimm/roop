"""Domain records, including a soft-delete flag on items."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Item:
    id: int
    sku: str
    name: str
    quantity: int
    price_cents: int
    deleted: bool = False
