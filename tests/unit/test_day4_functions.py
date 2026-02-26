"""
Extended edge-case unit tests for exercises/day4_functions.py.

These complement the baseline tests in test_utils.py by covering
boundary conditions, type guards, unicode, and numeric edge cases.
Each group targets a different aspect of each function than the
corresponding test in test_utils.py.
"""

import math
import pytest

from exercises.day4_functions import (
    validate_email,
    is_positive,
    format_price,
    is_even,
    normalize_name,
)


# ================================================================
# validate_email
# ================================================================

def test_email_with_subdomain_is_valid():
    assert validate_email("user@sub.domain.com") is True


def test_email_with_plus_sign_returns_false():
    # The regex [\w\.-]+ does not include '+', so plus-sign addresses
    # are not matched by this validator.
    assert validate_email("user+tag@domain.com") is False


def test_email_with_numbers_is_valid():
    assert validate_email("user123@domain456.org") is True


def test_email_with_dots_in_local_is_valid():
    assert validate_email("first.last@domain.com") is True


def test_email_none_returns_false():
    assert validate_email(None) is False


def test_email_integer_returns_false():
    assert validate_email(42) is False


def test_email_at_only_returns_false():
    assert validate_email("@") is False


def test_email_no_at_sign_returns_false():
    assert validate_email("notanemail") is False


def test_email_empty_string_returns_false():
    assert validate_email("") is False


def test_email_double_at_returns_false():
    assert validate_email("user@@domain.com") is False


# ================================================================
# is_positive
# ================================================================

def test_is_positive_zero_is_false():
    assert is_positive(0) is False


def test_is_positive_tiny_float_is_true():
    assert is_positive(0.0001) is True


def test_is_positive_negative_float_is_false():
    assert is_positive(-0.5) is False


def test_is_positive_nan_is_false():
    assert is_positive(float("nan")) is False


def test_is_positive_positive_infinity_is_true():
    assert is_positive(float("inf")) is True


def test_is_positive_negative_infinity_is_false():
    assert is_positive(float("-inf")) is False


def test_is_positive_bool_true_is_rejected():
    # bool is a subclass of int; the function explicitly rejects it
    assert is_positive(True) is False


def test_is_positive_bool_false_is_rejected():
    assert is_positive(False) is False


def test_is_positive_string_is_false():
    assert is_positive("5") is False


# ================================================================
# format_price
# ================================================================

def test_format_price_zero_gives_two_decimals():
    assert format_price(0) == "$0.00"


def test_format_price_negative_value():
    assert format_price(-9.99) == "$-9.99"


def test_format_price_rounds_half_down():
    assert format_price(5.554) == "$5.55"


def test_format_price_rounds_half_up():
    assert format_price(5.555) == "$5.56"


def test_format_price_large_number():
    assert format_price(99999.99) == "$99999.99"


def test_format_price_bool_raises_type_error():
    with pytest.raises(TypeError):
        format_price(True)


def test_format_price_non_numeric_string_raises_type_error():
    with pytest.raises(TypeError):
        format_price("abc")


def test_format_price_none_raises_type_error():
    with pytest.raises(TypeError):
        format_price(None)


# ================================================================
# is_even
# ================================================================

def test_is_even_zero_is_true():
    assert is_even(0) is True


def test_is_even_negative_even_is_true():
    assert is_even(-4) is True


def test_is_even_negative_odd_is_false():
    assert is_even(-3) is False


def test_is_even_bool_true_is_rejected():
    assert is_even(True) is False


def test_is_even_bool_false_is_rejected():
    assert is_even(False) is False


def test_is_even_float_is_rejected():
    # 2.0 looks even but is not int
    assert is_even(2.0) is False


def test_is_even_string_is_rejected():
    assert is_even("2") is False


# ================================================================
# normalize_name
# ================================================================

def test_normalize_empty_string_returns_empty():
    assert normalize_name("") == ""


def test_normalize_unicode_accented():
    assert normalize_name("josé") == "José"


def test_normalize_apostrophe():
    assert normalize_name("o'brien") == "O'Brien"


def test_normalize_all_caps_to_title():
    assert normalize_name("JOHN DOE") == "John Doe"


def test_normalize_whitespace_only_returns_empty():
    assert normalize_name("   ") == ""


def test_normalize_mixed_case_with_leading_spaces():
    assert normalize_name("  alice SMITH  ") == "Alice Smith"


def test_normalize_integer_raises_type_error():
    with pytest.raises(TypeError):
        normalize_name(42)


def test_normalize_list_raises_type_error():
    with pytest.raises(TypeError):
        normalize_name(["john"])
