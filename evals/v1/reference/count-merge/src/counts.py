def parse_counts(text: str) -> dict[str, int]:
    if text.strip() == '':
        return {}
    counts: dict[str, int] = {}
    for part in text.split(','):
        if ':' not in part:
            raise ValueError('missing colon')
        key, raw = part.split(':', 1)
        key = key.strip()
        raw = raw.strip()
        if not key or not raw.isdigit():
            raise ValueError('invalid count')
        counts[key] = counts.get(key, 0) + int(raw)
    return counts
