import datetime
import sqlite3
import pytest
from app.utils.sender import execute_send
from app.services.base import NotificationService


class FailSMS(NotificationService):
    name = "sms"
    enabled = True
    def send(self, person, message, **context):
        self._reset()
        self.last_error = "boom"
        return False
    def health_check(self): return False


def test_send_writes_log_on_success(db, mock_sms_service):
    person = dict(db.execute("SELECT * FROM people WHERE id=1").fetchone())
    execute_send(db, person, "birthday", "same_day", "Happy Birthday!", [mock_sms_service], write_state=True)
    log = db.execute("SELECT * FROM notification_log WHERE person_id=1").fetchone()
    assert log["status"] == "sent"
    assert log["channel"] == "sms"


def test_send_writes_state_on_success(db, mock_sms_service):
    person = dict(db.execute("SELECT * FROM people WHERE id=1").fetchone())
    execute_send(db, person, "birthday", "same_day", "Happy Birthday!", [mock_sms_service], write_state=True)
    state = db.execute("SELECT * FROM notification_state WHERE person_id=1").fetchone()
    assert state is not None
    assert state["channel"] == "sms"


def test_send_skips_if_state_exists(db, mock_sms_service):
    year = datetime.date.today().year
    db.execute("INSERT INTO notification_state (person_id, event_type, trigger_type, channel, year_sent) VALUES (1,'birthday','same_day','sms',?)", (year,))
    db.commit()
    person = dict(db.execute("SELECT * FROM people WHERE id=1").fetchone())
    execute_send(db, person, "birthday", "same_day", "msg", [mock_sms_service], write_state=True)
    assert len(mock_sms_service.calls) == 0


def test_failed_send_writes_log_no_state(db):
    person = dict(db.execute("SELECT * FROM people WHERE id=1").fetchone())
    execute_send(db, person, "birthday", "same_day", "msg", [FailSMS()], write_state=True)
    log = db.execute("SELECT * FROM notification_log WHERE person_id=1").fetchone()
    assert log["status"] == "failed"
    state = db.execute("SELECT * FROM notification_state WHERE person_id=1").fetchone()
    assert state is None


def test_write_state_false_does_not_write_state(db, mock_sms_service):
    person = dict(db.execute("SELECT * FROM people WHERE id=1").fetchone())
    execute_send(db, person, "birthday", "7_day", "msg", [mock_sms_service], write_state=False)
    state = db.execute("SELECT * FROM notification_state WHERE person_id=1").fetchone()
    assert state is None
    log = db.execute("SELECT * FROM notification_log WHERE person_id=1").fetchone()
    assert log["status"] == "sent"


def test_already_sent_returns_true_when_state_exists(db):
    from app.utils.sender import already_sent
    year = datetime.date.today().year
    db.execute("INSERT INTO notification_state (person_id, event_type, trigger_type, channel, year_sent) VALUES (1,'birthday','same_day','sms',?)", (year,))
    db.commit()
    assert already_sent(db, 1, "birthday", "same_day", "sms") is True


def test_already_sent_returns_false_when_no_state(db):
    from app.utils.sender import already_sent
    assert already_sent(db, 1, "birthday", "same_day", "sms") is False
