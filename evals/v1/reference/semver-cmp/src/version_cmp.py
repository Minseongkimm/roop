from src.semver import parse_semver


def compare_semver(left: str, right: str) -> int:
    parsed_left: tuple[int, int, int] = parse_semver(left)
    parsed_right: tuple[int, int, int] = parse_semver(right)
    if parsed_left < parsed_right:
        return -1
    if parsed_left > parsed_right:
        return 1
    return 0
