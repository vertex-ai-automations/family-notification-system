import datetime
import sqlite3
from unittest.mock import MagicMock, patch
from app.database import create_tables, seed_settings, get_connection
from app.scheduler import run_advance_reminders, run_day_of_wishes, days_until


def make_db():
    conn = get_connection(":memory:")
    create_tables(conn)
    seed_settings(conn)
    return conn


def test_days_until_future_date():
    today = datetime.date.today()
    future = (today + datetime.timedelta(days=7)).strftime("%m-%d")
    assert days_until(future) == 7


def test_days_until_today():
    today = datetime.date.today().strftime("%m-%d")
    assert days_until(today) == 0


def test_days_until_wraps_to_next_year():
    # A date that already passed this year should return days until next year
    today = datetime.date.today()
    past = (today - datetime.timedelta(days=1)).strftime("%m-%d")
    result = days_until(past)
    assert result > 300  # wraps to next year


def test_advance_reminder_sends_to_others():
    db = make_db()
    today = datetime.date.today()
    in_7 = (today + datetime.timedelta(days=7)).strftime("%m-%d")
    db.execute("INSERT INTO people (name, phone, birthday) VALUES ('Birthday Person', '+10000000001', ?)", (in_7,))
    db.execute("INSERT INTO people (name, phone, birthday) VALUES ('Other Family', '+10000000002', '06-15')")
    db.commit()

    mock_service = MagicMock()
    mock_service.name = "sms"
    mock_service.enabled = True
    mock_service.send.return_value = True

    with patch("app.scheduler.get_services", return_value=[mock_service]):
        with patch("app.scheduler.get_db", return_value=db):
            run_advance_reminders()

    assert mock_service.send.call_count == 1
    call_person = mock_service.send.call_args[0][0]
    assert call_person["name"] == "Other Family"


def test_advance_reminder_does_not_send_to_birthday_person():
    db = make_db()
    today = datetime.date.today()
    in_7 = (today + datetime.timedelta(days=7)).strftime("%m-%d")
    db.execute("INSERT INTO people (name, phone, birthday) VALUES ('Birthday Person', '+10000000001', ?)", (in_7,))
    db.commit()

    mock_service = MagicMock()
    mock_service.name = "sms"
    mock_service.enabled = True
    mock_service.send.return_value = True

    with patch("app.scheduler.get_services", return_value=[mock_service]):
        with patch("app.scheduler.get_db", return_value=db):
            run_advance_reminders()

    # Only 1 person and it's the birthday person — should send to 0 recipients
    assert mock_service.send.call_count == 0


def test_day_of_wishes_sends_to_birthday_person():
    db = make_db()
    today = datetime.date.today().strftime("%m-%d")
    db.execute("INSERT INTO people (name, phone, birthday) VALUES ('Birthday Person', '+10000000001', ?)", (today,))
    db.execute("INSERT INTO people (name, phone, birthday) VALUES ('Other Family', '+10000000002', '06-15')")
    db.commit()

    mock_service = MagicMock()
    mock_service.name = "sms"
    mock_service.enabled = True
    mock_service.send.return_value = True

    with patch("app.scheduler.get_services", return_value=[mock_service]):
        with patch("app.scheduler.get_db", return_value=db):
            run_day_of_wishes()

    assert mock_service.send.call_count == 1
    call_person = mock_service.send.call_args[0][0]
    assert call_person["name"] == "Birthday Person"


def test_paused_person_skipped():
    db = make_db()
    today = datetime.date.today().strftime("%m-%d")
    db.execute(
        "INSERT INTO people (name, phone, birthday, notifications_paused) VALUES ('Paused', '+10000000001', ?, 1)",
        (today,),
    )
    db.commit()

    mock_service = MagicMock()
    mock_service.name = "sms"
    mock_service.enabled = True
    mock_service.send.return_value = True

    with patch("app.scheduler.get_services", return_value=[mock_service]):
        with patch("app.scheduler.get_db", return_value=db):
            run_day_of_wishes()

    assert mock_service.send.call_count == 0


def test_anniversary_reminder_only_sent_when_married():
    db = make_db()
    today = datetime.date.today()
    in_7 = (today + datetime.timedelta(days=7)).strftime("%m-%d")
    # married=0, has anniversary date — should NOT send anniversary reminder
    db.execute(
        "INSERT INTO people (name, phone, birthday, married, anniversary) VALUES ('Person', '+10000000001', '06-15', 0, ?)",
        (in_7,),
    )
    db.execute("INSERT INTO people (name, phone, birthday) VALUES ('Other', '+10000000002', '06-20')")
    db.commit()

    mock_service = MagicMock()
    mock_service.name = "sms"
    mock_service.enabled = True
    mock_service.send.return_value = True

    with patch("app.scheduler.get_services", return_value=[mock_service]):
        with patch("app.scheduler.get_db", return_value=db):
            run_advance_reminders()

    assert mock_service.send.call_count == 0
