import sqlite3

DB_PATH = "data/family.db"

def get_connection(path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    if path != ":memory:":
        conn.execute("PRAGMA journal_mode=WAL")
    return conn

def create_tables(conn: sqlite3.Connection):
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS people (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT,
        email TEXT,
        whatsapp TEXT,
        birthday TEXT NOT NULL,
        birth_year INTEGER,
        married BOOLEAN DEFAULT 0,
        spouse_name TEXT,
        anniversary TEXT,
        anniversary_year INTEGER,
        custom_birthday_message TEXT DEFAULT '',
        custom_anniversary_message TEXT DEFAULT '',
        notifications_paused BOOLEAN DEFAULT 0,
        mother_id INTEGER REFERENCES people(id) ON DELETE SET NULL,
        father_id INTEGER REFERENCES people(id) ON DELETE SET NULL,
        spouse_id INTEGER REFERENCES people(id) ON DELETE SET NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS notification_state (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        person_id INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE,
        event_type TEXT NOT NULL,
        trigger_type TEXT NOT NULL,
        channel TEXT NOT NULL,
        year_sent INTEGER NOT NULL,
        sent_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(person_id, event_type, trigger_type, channel, year_sent)
    );
    CREATE TABLE IF NOT EXISTS notification_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        person_id INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE,
        event_type TEXT NOT NULL,
        trigger_type TEXT NOT NULL,
        channel TEXT NOT NULL,
        message_body TEXT NOT NULL,
        status TEXT NOT NULL,
        error_message TEXT,
        sent_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_log_person_sent ON notification_log(person_id, sent_at DESC);
    CREATE INDEX IF NOT EXISTS idx_log_status ON notification_log(status);
    CREATE INDEX IF NOT EXISTS idx_people_mother ON people(mother_id);
    CREATE INDEX IF NOT EXISTS idx_people_father ON people(father_id);
    CREATE INDEX IF NOT EXISTS idx_people_spouse ON people(spouse_id);
    """)
    conn.commit()


def migrate(conn: sqlite3.Connection):
    """Idempotent column-adders for existing databases.
    SQLite ALTER TABLE … ADD COLUMN ignores REFERENCES at runtime, so we add as
    plain INTEGER and rely on app-level enforcement. Indexes get created here
    too (CREATE INDEX IF NOT EXISTS is idempotent)."""
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(people)").fetchall()}
    for col in ("mother_id", "father_id", "spouse_id"):
        if col not in cols:
            conn.execute(f"ALTER TABLE people ADD COLUMN {col} INTEGER")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_people_mother ON people(mother_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_people_father ON people(father_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_people_spouse ON people(spouse_id)")
    conn.commit()


DEFAULTS = {
    "advance_days_week": "7",
    "advance_days_day": "1",
    "job1_time": "08:00",
    "job2_time": "12:00",
    "catch_up_hours": "6",
    "sms_enabled": "true",
    "whatsapp_enabled": "true",
    "email_enabled": "true",
}

def seed_settings(conn: sqlite3.Connection):
    for key, value in DEFAULTS.items():
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()

def init_db(path: str = DB_PATH):
    import os
    dir_name = os.path.dirname(path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    conn = get_connection(path)
    create_tables(conn)
    migrate(conn)
    seed_settings(conn)
    return conn
