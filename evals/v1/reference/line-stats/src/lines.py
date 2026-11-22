def split_lines(text: str) -> list[str]:
    if text == '':
        return []
    if text.endswith('\n'):
        text = text[:-1]
    return text.split('\n')
