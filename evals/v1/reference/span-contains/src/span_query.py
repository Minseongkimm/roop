from src.span import parse_span


def span_contains(span: str, point: int) -> bool:
    if isinstance(point, bool) or not isinstance(point, int):
        raise ValueError('invalid point')
    start, end = parse_span(span)
    return start <= point <= end
