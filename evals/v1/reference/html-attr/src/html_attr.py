import re

from src.html_escape import escape_text


def render_attr(name: str, value: str) -> str:
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*', name):
        raise ValueError('invalid attribute name')
    return name + '="' + escape_text(value) + '"'
