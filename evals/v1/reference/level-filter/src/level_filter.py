from src.level import parse_level


def filter_lines(lines: list[str], minimum: str) -> list[str]:
    threshold: int = parse_level(minimum)
    kept: list[str] = []
    for line in lines:
        parts: list[str] = line.split(' ', 1)
        if len(parts) != 2 or not parts[1].strip():
            raise ValueError('invalid line')
        if parse_level(parts[0]) >= threshold:
            kept.append(line)
    return kept
