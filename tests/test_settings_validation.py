def test_settings_rejects_unknown_key(client):
    r = client.put("/api/settings", json={"unknown_key": "value"})
    assert r.status_code == 400


def test_settings_rejects_bad_time_format(client):
    r = client.put("/api/settings", json={"job1_time": "8am"})
    assert r.status_code == 400


def test_settings_accepts_valid_time(client):
    r = client.put("/api/settings", json={"job1_time": "09:30"})
    assert r.status_code == 200
    assert client.get("/api/settings").json()["job1_time"] == "09:30"


def test_settings_rejects_non_integer_days(client):
    r = client.put("/api/settings", json={"advance_days_week": "seven"})
    assert r.status_code == 400


def test_settings_rejects_out_of_range_days(client):
    r = client.put("/api/settings", json={"advance_days_week": "999"})
    assert r.status_code == 400


def test_settings_rejects_invalid_bool(client):
    r = client.put("/api/settings", json={"sms_enabled": "yes"})
    assert r.status_code == 400


def test_settings_rejects_bad_catch_up_hours(client):
    r = client.put("/api/settings", json={"catch_up_hours": "100"})
    assert r.status_code == 400


def test_settings_partial_failure_rolls_back(client):
    # First valid update succeeds
    client.put("/api/settings", json={"job1_time": "09:00"})
    # Then bad update — both keys should fail to apply
    r = client.put("/api/settings", json={"job2_time": "10:00", "job1_time": "not-a-time"})
    assert r.status_code == 400
    # job1_time should still be the previous valid value, not "10:00" partial
    s = client.get("/api/settings").json()
    assert s["job1_time"] == "09:00"
