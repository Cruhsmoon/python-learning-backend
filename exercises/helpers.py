import re


def validate_email(email: str) -> bool:
    if not isinstance(email, str):
        return False

    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return bool(re.match(pattern, email))
def is_positive(number: float) -> bool:
    return number > 0
def format_price(price: float) -> str:
    return f"${price:.2f}"
def is_even(number: int) -> bool:
    return number % 2 == 0
def normalize_name(name: str) -> str:
    return name.strip().title()
