def join_url_path(*parts: str) -> str:
    cleaned: list[str] = []
    for part in parts:
        piece: str = part.strip().strip('/')
        if piece:
            cleaned.append(piece)
    if not cleaned:
        return ''
    joined: str = '/'.join(cleaned)
    if parts and parts[0].strip().startswith('/'):
        return '/' + joined
    return joined
