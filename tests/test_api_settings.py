def test_get_settings_returns_defaults(client):
    r = client.get("/api/settings")
    assert r.status_code == 200
    assert r.json()["advance_days_week"] == "7"

def test_update_settings(client):
    r = client.put("/api/settings", json={"advance_days_week": "14"})
    assert r.status_code == 200
    r2 = client.get("/api/settings")
    assert r2.json()["advance_days_week"] == "14"

def test_get_credentials_returns_masked(client):
    r = client.get("/api/credentials")
    assert r.status_code == 200
    data = r.json()
    assert "smtp_host" in data

def test_import_via_api(client):
    data = {
        "people": [
            {"name": "Import Test", "birthday": "07-04", "phone": "2125551234"}
        ]
    }
    r = client.post("/api/import", json=data)
    assert r.status_code == 200
    result = r.json()
    assert result["imported"] == 1

def test_export_via_api(client):
    r = client.get("/api/export")
    assert r.status_code == 200
    data = r.json()
    assert "people" in data
    assert "exported_at" in data
