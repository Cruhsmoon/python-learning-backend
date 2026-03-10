import re
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation


def validate_email(email: str) -> bool:
    if not isinstance(email, str):
        return False

    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return bool(re.match(pattern, email))


def is_positive(number: float) -> bool:
    if not isinstance(number, (int, float)) or isinstance(number, bool):
        return False

    return number > 0


def format_price(price) -> str:
    if isinstance(price, bool):
        raise TypeError("Bool is not allowed as price")

    try:
        decimal_price = Decimal(str(price))
    except (InvalidOperation, ValueError):
        raise TypeError("Price must be a valid number")

    rounded_price = decimal_price.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )

    return f"${rounded_price}"


def is_even(number: int) -> bool:
    if not isinstance(number, int) or isinstance(number, bool):
        return False

    return number % 2 == 0


def normalize_name(name: str) -> str:
    if not isinstance(name, str):
        raise TypeError("Name must be a string")

    return name.strip().title()


# ===========================
# ASSERT TESTS
# ===========================

if __name__ == "__main__":

    # validate_email
    assert validate_email(None) is False
    assert validate_email("") is False
    assert validate_email("user@domain.com") is True
    assert validate_email("user@domain") is False
    assert validate_email("üser@domain.com") is True

    # is_positive
    assert is_positive(0) is False
    assert is_positive(-1) is False
    assert is_positive(0.0001) is True
    assert is_positive(float("nan")) is False
    assert is_positive(True) is False  # теперь bool запрещён

    # format_price (Decimal version)
    assert format_price(0) == "$0.00"
    assert format_price(5.555) == "$5.56"
    assert format_price(5.554) == "$5.55"
    assert format_price(-9.99) == "$-9.99"

    try:
        format_price(True)
        assert False
    except TypeError:
        assert True

    try:
        format_price(None)
        assert False
    except TypeError:
        assert True

    # is_even
    assert is_even(0) is True
    assert is_even(3) is False
    assert is_even(-2) is True
    assert is_even(True) is False
    assert is_even(False) is False  # bool больше не считается int

    # normalize_name
    assert normalize_name("  henry web  ") == "Henry Web"
    assert normalize_name("") == ""
    assert normalize_name("josé") == "José"
    assert normalize_name("o'brien") == "O'Brien"

    try:
        normalize_name(None)
        assert False
    except TypeError:
        assert True

    print("All tests passed successfully.")