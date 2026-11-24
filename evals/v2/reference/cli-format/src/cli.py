"""Command-line front end for the inventory service."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, TextIO

from src.models import Item
from src.service import InventoryService

TABLE_HEADER: str = "ID\tSKU\tNAME\tQTY\tPRICE"


def format_table(items: list[Item]) -> str:
    lines: list[str] = [TABLE_HEADER]
    for item in items:
        lines.append(
            f"{item.id}\t{item.sku}\t{item.name}\t{item.quantity}\t{item.price_cents}"
        )
    return "\n".join(lines)


def format_json(items: list[Item]) -> str:
    payload: list[dict[str, object]] = [
        {
            "id": item.id,
            "sku": item.sku,
            "name": item.name,
            "quantity": item.quantity,
            "price_cents": item.price_cents,
        }
        for item in items
    ]
    return json.dumps(payload, separators=(",", ":"))


def build_parser() -> argparse.ArgumentParser:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(prog="inventory")
    sub: Any = parser.add_subparsers(dest="command", required=True)

    add: argparse.ArgumentParser = sub.add_parser("add")
    add.add_argument("--sku", required=True)
    add.add_argument("--name", required=True)
    add.add_argument("--quantity", type=int, required=True)
    add.add_argument("--price-cents", type=int, required=True, dest="price_cents")

    get: argparse.ArgumentParser = sub.add_parser("get")
    get.add_argument("item_id", type=int)

    listing: argparse.ArgumentParser = sub.add_parser("list")
    listing.add_argument(
        "--format",
        choices=("table", "json"),
        default="table",
        dest="list_format",
    )

    adjust: argparse.ArgumentParser = sub.add_parser("adjust")
    adjust.add_argument("item_id", type=int)
    adjust.add_argument("--delta", type=int, required=True)
    return parser


def main(
    argv: list[str] | None = None,
    *,
    service: InventoryService | None = None,
    stdout: TextIO | None = None,
) -> int:
    parser: argparse.ArgumentParser = build_parser()
    try:
        args: argparse.Namespace = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code or 0)
    svc: InventoryService = service or InventoryService()
    out: TextIO = stdout or sys.stdout
    if args.command == "add":
        item: Item = svc.create_item(
            args.sku, args.name, args.quantity, args.price_cents
        )
        out.write(f"{item.id}\t{item.sku}\t{item.name}\n")
        return 0
    if args.command == "get":
        try:
            found: Item = svc.get_item(args.item_id)
        except KeyError:
            out.write("not found\n")
            return 1
        out.write(
            f"{found.id}\t{found.sku}\t{found.name}\t"
            f"{found.quantity}\t{found.price_cents}\n"
        )
        return 0
    if args.command == "list":
        items: list[Item] = svc.list_items()
        if args.list_format == "json":
            out.write(format_json(items) + "\n")
        else:
            out.write(format_table(items) + "\n")
        return 0
    if args.command == "adjust":
        try:
            updated: Item = svc.adjust_stock(args.item_id, args.delta)
        except KeyError:
            out.write("not found\n")
            return 1
        except ValueError as exc:
            out.write(f"{exc}\n")
            return 1
        out.write(f"{updated.id}\t{updated.quantity}\n")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
