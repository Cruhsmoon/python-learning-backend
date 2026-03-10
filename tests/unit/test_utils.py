import pytest
from src.utils.functions import (
    validate_email,
    is_positive,
    format_price,
    is_even,
    normalize_name,
)


# ---------- validate_email ----------

def test_valid_email():
    assert validate_email("user@domain.com") is True


def test_invalid_email_no_domain():
    assert validate_email("user@domain") is False


# ---------- is_positive ----------

def test_positive_number():
    assert is_positive(10) is True


def test_negative_number():
    assert is_positive(-5) is False


# ---------- format_price ----------

def test_format_price_rounding():
    assert format_price(5.555) == "$5.56"


def test_format_price_invalid_type():
    with pytest.raises(TypeError):
        format_price(None)


# ---------- is_even ----------

def test_even_number():
    assert is_even(4) is True


def test_odd_number():
    assert is_even(3) is False


# ---------- normalize_name ----------

def test_normalize_name():
    assert normalize_name("  john doe  ") == "John Doe"


def test_normalize_invalid_type():
    with pytest.raises(TypeError):
        normalize_name(None)
