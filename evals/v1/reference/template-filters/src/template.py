"""Replace {{ name }} and {{ name|filter:arg }} tags."""

from __future__ import annotations

import re

from src.filters import apply_filter

_TAG: re.Pattern[str] = re.compile(r"\{\{(.*?)\}\}")


def render(template: str, values: dict[str, str]) -> str:
    if template.count("{{") != template.count("}}"):
        raise ValueError("unclosed tag")

    def replace(match: re.Match[str]) -> str:
        body: str = match.group(1).strip()
        if "|" not in body:
            if body not in values:
                raise KeyError(body)
            return str(values[body])
        name, filter_part = body.split("|", 1)
        name = name.strip()
        filter_part = filter_part.strip()
        if ":" in filter_part:
            filter_name, arg = filter_part.split(":", 1)
            filter_name = filter_name.strip()
        else:
            filter_name, arg = filter_part, ""
        if name not in values:
            if filter_name != "default":
                raise KeyError(name)
            current = ""
        else:
            current = str(values[name])
        return apply_filter(current, filter_name, arg)

    return _TAG.sub(replace, template)
