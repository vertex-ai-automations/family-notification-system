import datetime
import pytest
from fastapi.testclient import TestClient

def test_list_members_empty(client):
    r = client.get("/api/members")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    # conftest adds John, so list has 1 member
    assert len(r.json()) == 1

def test_create_member(client):
    r = client.post("/api/members", json={"name": "Jane", "birthday": "06-15", "phone": "2144047340"})
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Jane"
    assert data["phone"] == "+12144047340"

def test_update_member(client):
    # John already exists with id=1
    r = client.put("/api/members/1", json={"name": "John Updated", "birthday": "01-28"})
    assert r.status_code == 200
    assert r.json()["name"] == "John Updated"

def test_delete_member(client):
    r = client.post("/api/members", json={"name": "Temp", "birthday": "03-15"})
    mid = r.json()["id"]
    r2 = client.delete(f"/api/members/{mid}")
    assert r2.status_code == 204
    ids = [m["id"] for m in client.get("/api/members").json()]
    assert mid not in ids

def test_update_nonexistent_returns_404(client):
    r = client.put("/api/members/9999", json={"name": "Ghost", "birthday": "01-01"})
    assert r.status_code == 404

def test_delete_nonexistent_returns_404(client):
    r = client.delete("/api/members/9999")
    assert r.status_code == 404

def test_upcoming_events(client):
    today = datetime.date.today()
    in_5 = (today + datetime.timedelta(days=5)).strftime("%m-%d")
    client.post("/api/members", json={"name": "Soon Birthday", "birthday": in_5})
    r = client.get("/api/members/upcoming")
    assert r.status_code == 200
    names = [e["name"] for e in r.json()]
    assert "Soon Birthday" in names

def test_phone_normalization_on_create(client):
    r = client.post("/api/members", json={"name": "Bob", "birthday": "04-01", "phone": "(718) 879-0062"})
    assert r.json()["phone"] == "+17188790062"
