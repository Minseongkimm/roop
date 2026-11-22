def scan_words(text: str) -> list[str]:
    words: list[str] = []
    current: list[str] = []
    for char in text:
        if char.isalpha():
            current.append(char.lower())
            continue
        if current:
            words.append(''.join(current))
            current = []
    if current:
        words.append(''.join(current))
    return words
