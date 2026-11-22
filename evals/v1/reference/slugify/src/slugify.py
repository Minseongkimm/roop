"""Turn text into a lowercase hyphenated slug."""

from __future__ import annotations

import re


def slugify(text: str) -> str:
    lowered: str = text.lower().replace(" ", "-")
    cleaned: str = re.sub(r"[^a-z0-9-]", "", lowered)
    collapsed: str = re.sub(r"-{2,}", "-", cleaned).strip("-")
    return collapsed
