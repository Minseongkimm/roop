"""Dump nested dictionaries as INI text."""

from __future__ import annotations


def dump_ini(sections: dict[str, dict[str, str]]) -> str:
    if not sections:
        return ""
    lines: list[str] = []
    for key in sorted(sections.get("", {})):
        lines.append(f"{key}={sections[''][key]}")
    for name in sorted(section for section in sections if section != ""):
        lines.append(f"[{name}]")
        for key in sorted(sections[name]):
            lines.append(f"{key}={sections[name][key]}")
    return "\n".join(lines) + "\n"
