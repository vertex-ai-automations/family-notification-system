def test_patch_single_field(client):
    r = client.patch("/api/members/1", json={"notifications_paused": True})
    assert r.status_code == 200
    assert r.json()["notifications_paused"] == 1
    # other fields unchanged
    assert r.json()["name"] == "John"
    assert r.json()["birthday"] == "01-28"


def test_patch_normalizes_phone(client):
    r = client.patch("/api/members/1", json={"phone": "(212) 555-1212"})
    assert r.json()["phone"] == "+12125551212"


def test_patch_whatsapp_equals_existing_phone_dedups(client):
    # John's existing phone is +15555550100 (from conftest)
    # PATCH whatsapp to the same number — should be stored as NULL
    r = client.patch("/api/members/1", json={"whatsapp": "5555550100"})
    assert r.json()["whatsapp"] is None


def test_patch_whatsapp_different_kept(client):
    r = client.patch("/api/members/1", json={"whatsapp": "5555550199"})
    assert r.json()["whatsapp"] == "+15555550199"


def test_patch_nonexistent_returns_404(client):
    r = client.patch("/api/members/9999", json={"notifications_paused": True})
    assert r.status_code == 404


def test_patch_empty_payload_is_noop(client):
    before = client.get("/api/members").json()[0]
    r = client.patch("/api/members/1", json={})
    assert r.status_code == 200
    after = r.json()
    assert after["name"] == before["name"]
    assert after["birthday"] == before["birthday"]
