def _seed_logs(client):
    """Insert a few log rows directly via the DB this test client uses."""
    from app.api.deps import _db_path_value
    from app.database import get_connection
    conn = get_connection(_db_path_value())
    conn.executemany(
        "INSERT INTO notification_log (person_id, event_type, trigger_type, channel, message_body, status, error_message, sent_at) "
        "VALUES (?,?,?,?,?,?,?,?)",
        [
            (1, "birthday", "same_day", "sms", "Happy Birthday, John!", "sent", None, "2026-04-01 12:00:00"),
            (1, "birthday", "same_day", "email", "Happy Birthday!", "failed", "smtp closed", "2026-04-01 12:00:01"),
            (1, "birthday", "7_day",    "sms", "John's birthday in 7 days!", "sent", None, "2026-04-15 08:00:00"),
        ],
    )
    conn.commit()
    conn.close()


def test_export_csv_returns_attachment(client):
    _seed_logs(client)
    r = client.get("/api/logs/export.csv")
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    assert "attachment" in r.headers.get("content-disposition", "")
    assert ".csv" in r.headers["content-disposition"]


def test_export_csv_has_header_and_rows(client):
    _seed_logs(client)
    body = client.get("/api/logs/export.csv").text
    lines = body.strip().split("\n")
    assert lines[0] == "id,person_name,event_type,trigger_type,channel,status,message_body,error_message,sent_at"
    assert len(lines) == 4  # header + 3 rows


def test_export_csv_respects_filters(client):
    _seed_logs(client)
    r = client.get("/api/logs/export.csv?status=failed")
    lines = r.text.strip().split("\n")
    assert len(lines) == 2  # header + 1 failed row
    assert "smtp closed" in lines[1]


def test_export_csv_quotes_commas_in_message(client):
    from app.api.deps import _db_path_value
    from app.database import get_connection
    conn = get_connection(_db_path_value())
    conn.execute(
        "INSERT INTO notification_log (person_id, event_type, trigger_type, channel, message_body, status, sent_at) "
        "VALUES (1,'birthday','same_day','sms','Happy Birthday, John!','sent','2026-04-01 12:00:00')"
    )
    conn.commit()
    conn.close()
    body = client.get("/api/logs/export.csv").text
    # The message contains a comma — must be wrapped in quotes
    assert '"Happy Birthday, John!"' in body


def test_reset_deletes_all_logs(client):
    _seed_logs(client)
    assert len(client.get("/api/logs").json()) == 3
    r = client.delete("/api/logs")
    assert r.status_code == 200
    assert r.json()["deleted"] == 3
    assert client.get("/api/logs").json() == []


def test_reset_respects_filters(client):
    _seed_logs(client)
    r = client.delete("/api/logs?status=failed")
    assert r.status_code == 200
    assert r.json()["deleted"] == 1
    remaining = client.get("/api/logs").json()
    assert len(remaining) == 2
    assert all(l["status"] == "sent" for l in remaining)


def test_reset_preserves_notification_state(client):
    """Reset must NOT wipe notification_state — that table is the idempotency guard."""
    from app.api.deps import _db_path_value
    from app.database import get_connection
    conn = get_connection(_db_path_value())
    conn.execute(
        "INSERT INTO notification_state (person_id, event_type, trigger_type, channel, year_sent) "
        "VALUES (1,'birthday','same_day','sms',2026)"
    )
    conn.commit()
    conn.close()
    _seed_logs(client)
    client.delete("/api/logs")
    # State row must still be present
    conn = get_connection(_db_path_value())
    rows = conn.execute("SELECT COUNT(*) FROM notification_state").fetchone()[0]
    conn.close()
    assert rows == 1
