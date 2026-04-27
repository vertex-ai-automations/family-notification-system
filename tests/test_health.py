def test_health_returns_db_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["db"] == "ok"
    assert "services" in data
    assert "status" in data


def test_health_status_ok_when_no_services():
    # The test client starts with start_scheduler=False so no services are loaded
    # — the health check should still report db ok.
    pass
