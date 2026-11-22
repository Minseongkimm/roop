def parse_semver(text: str) -> tuple[int, int, int]:
    parts: list[str] = text.split('.')
    if len(parts) != 3 or any(not part.isdigit() for part in parts):
        raise ValueError('invalid semver')
    major, minor, patch = (int(part) for part in parts)
    return (major, minor, patch)
