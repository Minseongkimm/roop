from src.lines import split_lines


def count_nonempty(text: str) -> int:
    return sum(1 for line in split_lines(text) if line.strip())
