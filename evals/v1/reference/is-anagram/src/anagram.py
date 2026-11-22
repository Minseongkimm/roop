def _letters(text: str) -> list[str]:
    return sorted(char.lower() for char in text if char.isalnum())


def is_anagram(left: str, right: str) -> bool:
    return _letters(left) == _letters(right)
