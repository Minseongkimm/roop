"""Palindrome check that ignores case and non-alphanumeric characters."""

from __future__ import annotations


def is_palindrome(text: str) -> bool:
    characters: list[str] = [char.lower() for char in text if char.isalnum()]
    return characters == list(reversed(characters))
