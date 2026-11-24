"""Trivial stub: --format is accepted but list always prints the table."""

from __future__ import annotations

import argparse
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
    del args  # format is ignored
    svc: InventoryService = service or InventoryService()
    out: TextIO = stdout or sys.stdout
    if parser.parse_args(argv).command == "list":
        out.write(format_table(svc.list_items()) + "\n")
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
