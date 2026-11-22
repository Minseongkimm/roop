def parse_int_list(text: str) -> list[int]:
    if text.strip() == '':
        return []
    values: list[int] = []
    for part in text.split(','):
        piece: str = part.strip()
        body: str = piece[1:] if piece.startswith('-') else piece
        if piece == '' or piece == '-' or not body.isdigit():
            raise ValueError('invalid integer list')
        values.append(int(piece))
    return values
