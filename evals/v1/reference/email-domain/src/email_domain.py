from src.email_split import split_email


def same_domain(left: str, right: str) -> bool:
    return split_email(left)[1] == split_email(right)[1]
