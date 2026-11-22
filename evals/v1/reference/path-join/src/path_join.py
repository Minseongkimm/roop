from src.path_clean import clean_segment


def join_path(segments: list[str]) -> str:
    if not segments:
        raise ValueError('empty path')
    return '/'.join(clean_segment(segment) for segment in segments)
