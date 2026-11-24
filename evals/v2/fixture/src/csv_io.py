"""CSV import and export for items. Both functions are stubs."""

from __future__ import annotations

from src.models import Item


def export_csv(items: list[Item]) -> str:
    raise NotImplementedError("export_csv is not implemented")


def import_csv(text: str) -> list[dict[str, object]]:
    raise NotImplementedError("import_csv is not implemented")
