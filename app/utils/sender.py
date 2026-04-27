import datetime
import sqlite3
import threading
from typing import List
from app.services.base import NotificationService

# In-process per-(person, event, trigger) lock — prevents rapid double-click
# from issuing two parallel sends before either has written notification_state.
_send_locks: dict[tuple[int, str, str], threading.Lock] = {}
_locks_guard = threading.Lock()


def _get_lock(person_id: int, event_type: str, trigger_type: str) -> threading.Lock:
    key = (person_id, event_type, trigger_type)
    with _locks_guard:
        lock = _send_locks.get(key)
        if lock is None:
            lock = threading.Lock()
            _send_locks[key] = lock
        return lock


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
    days: int = 0,
):
    year = datetime.date.today().year
    lock = _get_lock(person["id"], event_type, trigger_type)
    with lock:
        for service in services:
            if not service.enabled:
                continue
            if write_state and already_sent(db, person["id"], event_type, trigger_type, service.name):
                continue
            success = service.send(
                person,
                message,
                event_type=event_type,
                trigger_type=trigger_type,
                days=days,
            )
            if service.last_skip:
                # No contact field — silent skip, no log row.
                continue
            db.execute(
                "INSERT INTO notification_log (person_id, event_type, trigger_type, channel, message_body, status, error_message) VALUES (?,?,?,?,?,?,?)",
                (
                    person["id"],
                    event_type,
                    trigger_type,
                    service.name,
                    message,
                    "sent" if success else "failed",
                    None if success else service.last_error,
                ),
            )
            if success and write_state:
                db.execute(
                    "INSERT OR IGNORE INTO notification_state (person_id, event_type, trigger_type, channel, year_sent) VALUES (?,?,?,?,?)",
                    (person["id"], event_type, trigger_type, service.name, year),
                )
        db.commit()
