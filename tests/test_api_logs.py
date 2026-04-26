def test_list_logs_empty(client):
    r = client.get("/api/logs")
    assert r.status_code == 200
    assert r.json() == []

def test_list_logs_filter_by_channel(client):
    r = client.get("/api/logs?channel=sms")
    assert r.status_code == 200
