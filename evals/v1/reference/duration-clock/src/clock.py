from src.duration import parse_duration


def add_minutes(hhmm: str, duration: str) -> str:
    if len(hhmm) != 5 or hhmm[2] != ':' or not hhmm[:2].isdigit() or not hhmm[3:].isdigit():
        raise ValueError('invalid clock')
    hour: int = int(hhmm[:2])
    minute: int = int(hhmm[3:])
    if hour > 23 or minute > 59:
        raise ValueError('invalid clock')
    total: int = (hour * 60 + minute + parse_duration(duration)) % (24 * 60)
    return f'{total // 60:02d}:{total % 60:02d}'
