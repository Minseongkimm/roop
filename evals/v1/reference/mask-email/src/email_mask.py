def mask_email(text: str) -> str:
    if text.count('@') != 1:
        raise ValueError('expected one @')
    local, domain = text.split('@')
    if not local or not domain:
        raise ValueError('empty local or domain')
    stars: str = '*' * max(1, len(local) - 1)
    return local[0] + stars + '@' + domain
