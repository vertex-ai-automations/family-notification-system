import os, pytest
from app.config import get_config, hot_reload

def test_config_loads_from_env(monkeypatch):
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "ACtest123")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "token123")
    hot_reload()
    cfg = get_config()
    assert cfg.twilio_account_sid == "ACtest123"

def test_config_missing_optional_fields_are_none(monkeypatch):
    monkeypatch.delenv("SMTP_HOST", raising=False)
    hot_reload()
    cfg = get_config()
    assert cfg.smtp_host is None
