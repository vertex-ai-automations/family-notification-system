import sqlite3
import pytest
from fastapi.testclient import TestClient
from app.database import create_tables, seed_settings, get_connection
from app.services.base import NotificationService


@pytest.fixture
def db():
    conn = get_connection(":memory:")
    create_tables(conn)
    seed_settings(conn)
    conn.execute("INSERT INTO people (name, phone, email, birthday) VALUES ('John', '+17188790062', 'john@test.com', '01-28')")
    conn.commit()
    yield conn
    conn.close()


@pytest.fixture
def client(tmp_path):
    db_path = str(tmp_path / "test.db")
    conn = get_connection(db_path)
    create_tables(conn)
    seed_settings(conn)
    conn.execute("INSERT INTO people (name, phone, email, birthday) VALUES ('John', '+17188790062', 'john@test.com', '01-28')")
    conn.commit()
    conn.close()
    from app.main import create_app
    from fastapi.testclient import TestClient
    return TestClient(create_app(db_path=db_path, start_scheduler=False))


@pytest.fixture
def mock_sms_service():
    class MockSMS(NotificationService):
        name = "sms"
        enabled = True
        calls = []
        def send(self, person, message):
            self.calls.append((person["name"], message))
            return True
        def health_check(self):
            return True
    svc = MockSMS()
    svc.calls = []
    return svc
