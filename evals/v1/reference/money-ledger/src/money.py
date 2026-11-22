"""Parse and format money amounts as integer cents."""

from __future__ import annotations

import re

_AMOUNT: re.Pattern[str] = re.compile(
    r"^(-)?(?:(\d+)(?:\.(\d{1,2}))?|\.(\d{1,2}))$"
)


def parse_cents(text: str) -> int:
    raw: str = text.strip()
    if raw.startswith("$"):
        raw = raw[1:].strip()
    match: re.Match[str] | None = _AMOUNT.fullmatch(raw)
    if match is None:
        raise ValueError(f"invalid money: {text!r}")
    sign, whole, fraction, leading_fraction = match.groups()
    if leading_fraction is not None:
        cents: int = int(leading_fraction.ljust(2, "0"))
    else:
        cents = int(whole or "0") * 100
        if fraction:
            cents += int(fraction.ljust(2, "0"))
    if sign:
        return -cents
    return cents


def format_cents(cents: int) -> str:
    sign: str = "-" if cents < 0 else ""
    absolute: int = abs(int(cents))
    return f"{sign}{absolute // 100}.{absolute % 100:02d}"
