from app.database import get_connection

_db_path = "data/family.db"

def set_db_path(path: str):
    global _db_path
    _db_path = path

def get_db():
    conn = get_connection(_db_path)
    try:
        yield conn
    finally:
        conn.close()
