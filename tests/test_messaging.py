import datetime
from app.utils.messaging import render_message, get_default_message

def test_render_name_variable():
    assert render_message("Happy Birthday {name}!", {"name": "John"}, days=0) == "Happy Birthday John!"

def test_render_age_variable():
    birth_year = datetime.date.today().year - 40
    result = render_message("{name} is {age}!", {"name": "John", "birth_year": birth_year}, days=0)
    assert result == "John is 40!"

def test_render_missing_birth_year_omits_age():
    result = render_message("{name} is {age}!", {"name": "John", "birth_year": None}, days=0)
    assert "{age}" not in result

def test_render_days_variable():
    assert render_message("In {days} days!", {}, days=7) == "In 7 days!"

def test_render_years_married():
    ann_year = datetime.date.today().year - 10
    result = render_message("{years_married} years!", {"anniversary_year": ann_year}, days=0)
    assert result == "10 years!"

def test_default_birthday_advance():
    msg = get_default_message("birthday", "7_day", for_person=False)
    assert "{name}" in msg and "{days}" in msg

def test_default_birthday_same_day():
    msg = get_default_message("birthday", "same_day", for_person=True)
    assert "{name}" in msg and "Happy Birthday" in msg

def test_default_anniversary_advance():
    msg = get_default_message("anniversary", "1_day", for_person=False)
    assert "{name}" in msg and "{spouse}" in msg

def test_default_anniversary_same_day():
    msg = get_default_message("anniversary", "same_day", for_person=True)
    assert "Anniversary" in msg

def test_default_unknown_event_returns_none():
    assert get_default_message("nameday", "same_day", True) is None

def test_render_missing_birth_year_no_double_space():
    result = render_message("{name} is {age} years old!", {"name": "John", "birth_year": None}, days=0)
    assert "  " not in result
    assert "John" in result
