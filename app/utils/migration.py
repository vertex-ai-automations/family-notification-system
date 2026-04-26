import datetime
import sqlite3
from app.utils.phone import normalize_phone

def import_json(data: dict, db: sqlite3.Connection) -> dict:
    # Support both dict-of-dicts (old format) and list (new format)
    people_data = data.get("people", {})
    people_list = list(people_data.values()) if isinstance(people_data, dict) else people_data

    imported = 0
    skipped = 0
    year = datetime.date.today().year

    for p in people_list:
        name = p.get("name", "")
        if db.execute("SELECT id FROM people WHERE name=?", (name,)).fetchone():
            skipped += 1
            continue

        phone = normalize_phone(p.get("phone"))
        whatsapp = normalize_phone(p.get("whatsapp"))
        if whatsapp and whatsapp == phone:
            whatsapp = None
        married = bool(p.get("married", False))

        cursor = db.execute(
            """INSERT INTO people
               (name, phone, email, whatsapp, birthday, birth_year, married, spouse_name,
                anniversary, anniversary_year, custom_birthday_message, custom_anniversary_message)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (name, phone,
             p.get("email"), whatsapp,
             p.get("birthday", ""), p.get("birth_year"),
             married, p.get("spouse") or p.get("spouse_name"),
             p.get("anniversary"), p.get("anniversary_year"),
             p.get("custom_birthday_message", ""), p.get("custom_anniversary_message", ""))
        )
        person_id = cursor.lastrowid
        db.commit()
        imported += 1

        bday_notif = p.get("birthday_notification", {})
        if bday_notif.get("notified_week_before"):
            _write_state(db, person_id, "birthday", "7_day", "sms", year)
        if bday_notif.get("notified_day_before"):
            _write_state(db, person_id, "birthday", "1_day", "sms", year)

        ann_notif = p.get("anniversary_notification", {})
        if ann_notif.get("notified_week_before"):
            _write_state(db, person_id, "anniversary", "7_day", "sms", year)
        if ann_notif.get("notified_day_before"):
            _write_state(db, person_id, "anniversary", "1_day", "sms", year)

    return {"imported": imported, "skipped": skipped}

def _write_state(db, person_id, event_type, trigger_type, channel, year):
    db.execute(
        "INSERT OR IGNORE INTO notification_state (person_id, event_type, trigger_type, channel, year_sent) VALUES (?,?,?,?,?)",
        (person_id, event_type, trigger_type, channel, year)
    )
    db.commit()

def export_json(db: sqlite3.Connection) -> dict:
    people = [dict(r) for r in db.execute("SELECT * FROM people ORDER BY id").fetchall()]
    return {
        "exported_at": datetime.date.today().isoformat(),
        "people": people
    }
