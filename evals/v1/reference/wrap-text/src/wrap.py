def wrap_text(text: str, width: int) -> list[str]:
    if isinstance(width, bool) or not isinstance(width, int) or width < 1:
        raise ValueError('width must be >= 1')
    words: list[str] = text.split()
    if not words:
        return []
    lines: list[str] = []
    current: str = ''
    for word in words:
        if not current:
            current = word
            continue
        candidate: str = current + ' ' + word
        if len(candidate) <= width:
            current = candidate
            continue
        lines.append(current)
        current = word
    lines.append(current)
    return lines
