import re


def normalize_key(text: str) -> str:
    cleaned: str = re.sub(r'\s+', ' ', text.strip().lower())
    if not cleaned:
        raise ValueError('empty key')
    return cleaned
