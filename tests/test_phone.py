from app.utils.phone import normalize_phone

def test_10_digit_us_number():
    assert normalize_phone("7188790062") == "+17188790062"

def test_already_e164():
    assert normalize_phone("+17188790062") == "+17188790062"

def test_with_dashes():
    assert normalize_phone("718-879-0062") == "+17188790062"

def test_with_parens():
    assert normalize_phone("(718) 879-0062") == "+17188790062"

def test_none_returns_none():
    assert normalize_phone(None) is None

def test_empty_returns_none():
    assert normalize_phone("") is None

def test_whitespace_padded():
    assert normalize_phone("  +17188790062  ") == "+17188790062"

def test_too_short_returns_none():
    assert normalize_phone("12345") is None
