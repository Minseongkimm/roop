"""Write row dictionaries as CSV text."""

from __future__ import annotations

import csv
import io


def write_csv(rows: list[dict[str, str]], headers: list[str]) -> str:
    if not headers:
        raise ValueError("headers are required")
    buffer: io.StringIO = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
    writer.writerow(headers)
    for row in rows:
        writer.writerow([row.get(header, "") for header in headers])
    return buffer.getvalue()
