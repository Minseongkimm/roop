"""Domain records for the inventory service, including categories."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Item:
    id: int
    sku: str
    name: str
    quantity: int
    price_cents: int
    category_id: int | None = None


@dataclass(frozen=True, slots=True)
class Category:
    id: int
    name: str
    slug: str
