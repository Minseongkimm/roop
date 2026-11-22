def pad_left(text: str, width: int, fill: str = ' ') -> str:
    if isinstance(width, bool) or not isinstance(width, int) or width < 0:
        raise ValueError('width must be >= 0')
    if not isinstance(fill, str) or len(fill) != 1:
        raise ValueError('fill must be one character')
    if len(text) >= width:
        return text
    return fill * (width - len(text)) + text
