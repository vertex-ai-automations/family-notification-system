import datetime
import sqlite3
from apscheduler.schedulers.background import BackgroundScheduler
from app.database import get_connection
from app.utils.messaging import render_message, get_default_message
from app.utils.sender import execute_send

_scheduler = None
_services = []
_db_path = "data/family.db"


def get_db():
    return get_connection(_db_path)


def get_services():
    return _services


def days_until(date_str: str) -> int:
    today = datetime.date.today()
    month, day = map(int, date_str.split("-"))
    target = datetime.date(today.year, month, day)
    if target < today:
        target = datetime.date(today.year + 1, month, day)
    return (target - today).days


def _get_setting(db, key: str, default: str) -> str:
    row = db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row[0] if row else default


def run_advance_reminders():
    db = get_db()
    services = get_services()
    people = [dict(r) for r in db.execute("SELECT * FROM people WHERE notifications_paused=0").fetchall()]
    week_days = int(_get_setting(db, "advance_days_week", "7"))
    day_days = int(_get_setting(db, "advance_days_day", "1"))

    for person in people:
        for days_ahead, trigger_type in [(week_days, "7_day"), (day_days, "1_day")]:
            if person.get("birthday"):
                if days_until(person["birthday"]) == days_ahead:
                    template = (
                        person.get("custom_birthday_message")
                        or get_default_message("birthday", trigger_type, False)
                        or ""
                    )
                    message = render_message(template, person, days=days_ahead)
                    recipients = [p for p in people if p["id"] != person["id"]]
                    for recipient in recipients:
                        execute_send(db, recipient, "birthday", trigger_type, message, services, write_state=True)
            if person.get("married") and person.get("anniversary"):
                if days_until(person["anniversary"]) == days_ahead:
                    template = (
                        person.get("custom_anniversary_message")
                        or get_default_message("anniversary", trigger_type, False)
                        or ""
                    )
                    message = render_message(template, person, days=days_ahead)
                    recipients = [p for p in people if p["id"] != person["id"]]
                    for recipient in recipients:
                        execute_send(db, recipient, "anniversary", trigger_type, message, services, write_state=True)
    db.close()


def run_day_of_wishes():
    db = get_db()
    services = get_services()
    people = [dict(r) for r in db.execute("SELECT * FROM people WHERE notifications_paused=0").fetchall()]

    for person in people:
        if person.get("birthday") and days_until(person["birthday"]) == 0:
            template = (
                person.get("custom_birthday_message")
                or get_default_message("birthday", "same_day", True)
                or ""
            )
            message = render_message(template, person, days=0)
            execute_send(db, person, "birthday", "same_day", message, services, write_state=True)
        if person.get("married") and person.get("anniversary") and days_until(person["anniversary"]) == 0:
            template = (
                person.get("custom_anniversary_message")
                or get_default_message("anniversary", "same_day", True)
                or ""
            )
            message = render_message(template, person, days=0)
            execute_send(db, person, "anniversary", "same_day", message, services, write_state=True)
    db.close()


def setup_scheduler(services_list: list, db_path: str = "data/family.db"):
    global _scheduler, _services, _db_path
    _services = services_list
    _db_path = db_path

    db = get_db()        # use get_db() not get_connection() directly
    job1_time = _get_setting(db, "job1_time", "08:00")
    job2_time = _get_setting(db, "job2_time", "12:00")
    catch_up_hours = int(_get_setting(db, "catch_up_hours", "6"))
    db.close()

    j1_hour, j1_min = map(int, job1_time.split(":"))
    j2_hour, j2_min = map(int, job2_time.split(":"))

    _scheduler = BackgroundScheduler()
    _scheduler.add_job(run_advance_reminders, "cron", hour=j1_hour, minute=j1_min, id="advance_reminders")
    _scheduler.add_job(
        run_day_of_wishes,
        "cron",
        hour=j2_hour,
        minute=j2_min,
        id="day_of_wishes",
        misfire_grace_time=catch_up_hours * 3600,
    )
    _scheduler.start()


def stop_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown()
