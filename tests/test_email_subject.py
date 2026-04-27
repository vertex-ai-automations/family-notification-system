from app.config import get_config
from app.services.email_smtp import _build_subject


def test_birthday_same_day_subject():
    assert _build_subject({"name": "Anum"}, "birthday", "same_day", 0) == "Happy Birthday, Anum!"


def test_birthday_advance_subject():
    assert _build_subject({"name": "Anum"}, "birthday", "7_day", 7) == "Reminder: Anum's birthday in 7 day(s)"


def test_anniversary_same_day_subject():
    s = _build_subject({"name": "John", "spouse_name": "Jane"}, "anniversary", "same_day", 0)
    assert "Happy Anniversary" in s
    assert "John & Jane" in s


def test_anniversary_advance_subject():
    s = _build_subject({"name": "John", "spouse_name": "Jane"}, "anniversary", "1_day", 1)
    assert "Reminder" in s
    assert "John & Jane" in s
    assert "1 day(s)" in s


def test_unknown_event_falls_back():
    expected = f"{get_config().family_name} Notification"
    assert _build_subject({"name": "X"}, "graduation", "same_day", 0) == expected


def test_no_name_uses_family_fallback():
    assert "family" in _build_subject({}, "birthday", "same_day", 0).lower()
