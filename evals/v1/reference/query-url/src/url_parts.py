"""Split a URL into scheme, host, path, and query. Fragments are ignored."""

from __future__ import annotations


def split_url(url: str) -> dict[str, str]:
    text: str = url.split("#", 1)[0]
    if text.startswith("/"):
        path, _, query = text.partition("?")
        return {"scheme": "", "host": "", "path": path, "query": query}
    if "://" not in text:
        raise ValueError("missing scheme")
    scheme, rest = text.split("://", 1)
    if "/" in rest:
        host, path_and_query = rest.split("/", 1)
        path_and_query = f"/{path_and_query}"
    else:
        host, path_and_query = rest, ""
    if "@" in host:
        raise ValueError("userinfo is not allowed")
    path, _, query = path_and_query.partition("?")
    return {"scheme": scheme, "host": host, "path": path, "query": query}
