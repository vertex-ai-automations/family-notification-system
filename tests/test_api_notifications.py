import pytest

def test_preview_renders_message(client):
    r = client.post("/api/notifications/preview", json={
        "person_id": 1, "event_type": "birthday", "trigger_type": "same_day"
    })
    assert r.status_code == 200
    data = r.json()
    assert "John" in data["sms"]

def test_preview_nonexistent_person(client):
    r = client.post("/api/notifications/preview", json={
        "person_id": 9999, "event_type": "birthday", "trigger_type": "same_day"
    })
    assert r.status_code == 404

def test_pause_member(client):
    r = client.put("/api/members/1/pause", json={"paused": True})
    assert r.status_code == 200
    assert r.json()["notifications_paused"] == 1

def test_unpause_member(client):
    client.put("/api/members/1/pause", json={"paused": True})
    r = client.put("/api/members/1/pause", json={"paused": False})
    assert r.json()["notifications_paused"] == 0
