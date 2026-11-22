def is_balanced(text: str) -> bool:
    pairs: dict[str, str] = {')': '(', ']': '[', '}': '{'}
    stack: list[str] = []
    for char in text:
        if char in '([{':
            stack.append(char)
            continue
        if char not in pairs:
            continue
        if not stack or stack[-1] != pairs[char]:
            return False
        stack.pop()
    return not stack
