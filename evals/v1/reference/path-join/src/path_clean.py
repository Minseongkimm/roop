def clean_segment(segment: str) -> str:
    cleaned: str = segment.strip()
    if not cleaned or cleaned in {'.', '..'} or '/' in cleaned or '\\' in cleaned:
        raise ValueError('invalid segment')
    return cleaned
