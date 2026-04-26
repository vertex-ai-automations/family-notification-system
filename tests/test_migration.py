import datetime
from app.database import create_tables, seed_settings, get_connection
from app.utils.migration import import_json, export_json

SAMPLE = {
    "people": {
        "1": {
            "name": "John Doe",
            "phone": "7188790062",
            "birthday": "01-28",
            "birthday_notification": {"notified_week_before": True, "notified_day_before": False},
            "married": True,
            "spouse": "Venessa",
            "anniversary": "03-11",
            "anniversary_notification": {"notified_week_before": False, "notified_day_before": False}
        }
    }
}

def make_db():
    conn = get_connection(":memory:")
    create_tables(conn)
    seed_settings(conn)
    return conn

def test_import_creates_person():
    db = make_db()
    result = import_json(SAMPLE, db)
    assert result["imported"] == 1
    row = db.execute("SELECT * FROM people WHERE name='John Doe'").fetchone()
    assert row is not None
    assert row["phone"] == "+17188790062"

def test_import_writes_state_for_true_flags():
    db = make_db()
    import_json(SAMPLE, db)
    year = datetime.date.today().year
    state = db.execute(
        "SELECT * FROM notification_state WHERE trigger_type='7_day' AND channel='sms' AND year_sent=?", (year,)
    ).fetchone()
    assert state is not None

def test_import_deduplicates_by_name():
    db = make_db()
    import_json(SAMPLE, db)
    result2 = import_json(SAMPLE, db)
    assert result2["skipped"] == 1
    count = db.execute("SELECT COUNT(*) FROM people").fetchone()[0]
    assert count == 1

def test_export_roundtrip():
    db = make_db()
    import_json(SAMPLE, db)
    exported = export_json(db)
    assert len(exported["people"]) == 1
    assert exported["people"][0]["name"] == "John Doe"

def test_import_list_format():
    db = make_db()
    data = {"people": [{"name": "Alice", "birthday": "05-10", "phone": "2125551234"}]}
    result = import_json(data, db)
    assert result["imported"] == 1

def test_import_preserves_email():
    db = make_db()
    data = {"people": [{"name": "Alice", "birthday": "05-10", "email": "alice@test.com"}]}
    import_json(data, db)
    row = db.execute("SELECT email FROM people WHERE name='Alice'").fetchone()
    assert row["email"] == "alice@test.com"
