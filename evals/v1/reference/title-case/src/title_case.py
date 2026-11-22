def title_case(text: str) -> str:
    words: list[str] = text.split()
    return ' '.join(word[:1].upper() + word[1:].lower() for word in words)
