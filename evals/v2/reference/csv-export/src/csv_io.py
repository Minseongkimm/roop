"""CSV import and export for items."""

from __future__ import annotations

import csv
import io

from src.models import Item

HEADER: tuple[str, ...] = ("sku", "name", "quantity", "price_cents")


def export_csv(items: list[Item]) -> str:
    buffer: io.StringIO = io.StringIO()
    writer: csv.writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(HEADER)
    for item in items:
        writer.writerow((item.sku, item.name, item.quantity, item.price_cents))
    return buffer.getvalue()


def import_csv(text: str) -> list[dict[str, object]]:
    if not isinstance(text, str):
        raise ValueError("invalid csv")
    reader: csv.reader = csv.reader(io.StringIO(text))
    try:
        header: list[str] = next(reader)
    except StopIteration as exc:
        raise ValueError("missing header") from exc
    if tuple(header) != HEADER:
        raise ValueError("invalid header")
    rows: list[dict[str, object]] = []
    for raw in reader:
        if len(raw) != 4:
            raise ValueError("invalid row")
        sku, name, quantity_text, price_text = raw
        if not sku or not name:
            raise ValueError("invalid row")
        rows.append(
            {
                "sku": sku,
                "name": name,
                "quantity": _parse_int(quantity_text),
                "price_cents": _parse_int(price_text),
            }
        )
    return rows


def _parse_int(value: str) -> int:
    if value.startswith("-"):
        body: str = value[1:]
        if not body.isdigit():
            raise ValueError("invalid integer")
        return -int(body)
    if not value.isdigit():
        raise ValueError("invalid integer")
    return int(value)
