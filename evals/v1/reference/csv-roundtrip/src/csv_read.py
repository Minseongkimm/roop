"""Read CSV text into a list of row dictionaries."""

from __future__ import annotations

import csv
import io


def parse_csv(text: str) -> list[dict[str, str]]:
    if text.strip() == "":
        return []
    rows: list[list[str]] = list(csv.reader(io.StringIO(text)))
    if not rows:
        return []
    header: list[str] = rows[0]
    if len(header) != len(set(header)):
        raise ValueError("duplicate header")
    parsed: list[dict[str, str]] = []
    for row in rows[1:]:
        if len(row) > len(header):
            raise ValueError("too many fields")
        padded: list[str] = row + [""] * (len(header) - len(row))
        parsed.append(dict(zip(header, padded, strict=True)))
    return parsed
