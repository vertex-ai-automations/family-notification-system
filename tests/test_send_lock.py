import threading
import time
from app.services.base import NotificationService
from app.utils.sender import execute_send


class SlowMockService(NotificationService):
    """Mock that takes 100ms per send so we can detect concurrent execution."""
    name = "sms"
    enabled = True

    def __init__(self):
        self.in_flight = 0
        self.max_concurrent = 0
        self._lock = threading.Lock()
        self.calls = 0

    def send(self, person, message, **context):
        self._reset()
        with self._lock:
            self.in_flight += 1
            self.max_concurrent = max(self.max_concurrent, self.in_flight)
        try:
            time.sleep(0.05)
            self.calls += 1
            return True
        finally:
            with self._lock:
                self.in_flight -= 1

    def health_check(self):
        return True


def test_send_lock_serializes_same_person_event(db):
    """Two threads firing execute_send for the same (person, event, trigger) must serialize."""
    person = dict(db.execute("SELECT * FROM people WHERE id=1").fetchone())
    svc = SlowMockService()

    def run():
        # Each thread needs its own DB connection — re-open
        from app.database import get_connection, create_tables, seed_settings
        # Use the same in-memory DB by sharing the connection
        execute_send(db, person, "birthday", "same_day", "msg", [svc], write_state=False)

    threads = [threading.Thread(target=run) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Lock should have prevented concurrent service.send() executions
    assert svc.max_concurrent == 1
    assert svc.calls == 3
