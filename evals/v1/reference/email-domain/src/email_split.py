def split_email(text: str) -> tuple[str, str]:
    if text.count('@') != 1:
        raise ValueError('expected one @')
    local, domain = text.split('@')
    local = local.strip().lower()
    domain = domain.strip().lower()
    if not local or not domain or '.' not in domain or domain.startswith('.') or domain.endswith('.'):
        raise ValueError('invalid email')
    return (local, domain)
