import re


def normalize_sku(text: str) -> str:
    cleaned: str = text.strip().upper()
    if not re.fullmatch(r'[A-Z0-9]+(?:-[A-Z0-9]+)*', cleaned):
        raise ValueError('invalid sku')
    return cleaned
