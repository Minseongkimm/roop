from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Item:
    id: int
    sku: str
    name: str
    quantity: int
    price_cents: int


@dataclass(frozen=True, slots=True)
class OrderLine:
    item_id: int
    quantity: int
    unit_price_cents: int


@dataclass(frozen=True, slots=True)
class Order:
    id: int
    lines: tuple[OrderLine, ...]
    status: str
    total_cents: int
