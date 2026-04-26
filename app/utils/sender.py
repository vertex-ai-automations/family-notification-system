import datetime
import sqlite3
from typing import List
from app.services.base import NotificationService


def already_sent(db: sqlite3.Connection, person_id: int, event_type: str, trigger_type: str, channel: str) -> bool:
    year = datetime.date.today().year
    row = db.execute(
        "SELECT 1 FROM notification_state WHERE person_id=? AND event_type=? AND trigger_type=? AND channel=? AND year_sent=?",
        (person_id, event_type, trigger_type, channel, year)
    ).fetchone()
    return row is not None


def execute_send(
    db: sqlite3.Connection,
    person: dict,
    event_type: str,
    trigger_type: str,
    message: str,
    services: List[NotificationService],
    write_state: bool = True,
):
    year = datetime.date.today().year
    for service in services:
        if not service.enabled:
            continue
        if write_state and already_sent(db, person["id"], event_type, trigger_type, service.name):
            continue
        success = service.send(person, message)
        db.execute(
            "INSERT INTO notification_log (person_id, event_type, trigger_type, channel, message_body, status) VALUES (?,?,?,?,?,?)",
            (person["id"], event_type, trigger_type, service.name, message, "sent" if success else "failed")
        )
        if success and write_state:
            db.execute(
                "INSERT OR IGNORE INTO notification_state (person_id, event_type, trigger_type, channel, year_sent) VALUES (?,?,?,?,?)",
                (person["id"], event_type, trigger_type, service.name, year)
            )
    db.commit()
