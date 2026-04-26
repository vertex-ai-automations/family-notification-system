import sqlite3, pytest
from app.database import create_tables, seed_settings, get_connection

def test_tables_created(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "test.db"))
    create_tables(conn)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert {"people", "notification_state", "notification_log", "settings"} <= tables
    conn.close()

def test_notification_state_unique_constraint(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "test.db"))
    create_tables(conn)
    conn.execute("INSERT INTO people (name, birthday) VALUES ('Test', '01-01')")
    conn.execute("INSERT INTO notification_state (person_id, event_type, trigger_type, channel, year_sent) VALUES (1,'birthday','same_day','sms',2026)")
    conn.commit()
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO notification_state (person_id, event_type, trigger_type, channel, year_sent) VALUES (1,'birthday','same_day','sms',2026)")
        conn.commit()
    conn.close()

def test_seed_settings_inserts_defaults(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "test.db"))
    create_tables(conn)
    seed_settings(conn)
    row = conn.execute("SELECT value FROM settings WHERE key='advance_days_week'").fetchone()
    assert row[0] == "7"
    conn.close()
