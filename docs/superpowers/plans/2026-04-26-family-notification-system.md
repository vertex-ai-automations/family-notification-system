# Family Notification System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a self-hosted family birthday/anniversary notification system with a web dashboard, replacing two standalone Twilio scripts with a unified FastAPI app deployable on Raspberry Pi 5.

**Architecture:** FastAPI serves both the REST API and static dashboard from a single process. APScheduler fires two daily jobs inside FastAPI. SQLite stores all data. Three notification plugins (Twilio SMS, Twilio WhatsApp, SMTP Email) share a common interface — adding a new channel is one new file.

**Tech Stack:** Python 3.11+, FastAPI, uvicorn, APScheduler 3.x, SQLite (stdlib), python-dotenv, twilio, pytest, httpx

**Spec:** `docs/superpowers/specs/2026-04-26-family-notification-system-design.md`

---

## File Map

```
family-notification-system/
├── app/
│   ├── main.py                  # FastAPI app, startup/shutdown, route includes
│   ├── scheduler.py             # APScheduler jobs + wiring
│   ├── database.py              # SQLite connection, table creation, seed
│   ├── models.py                # Pydantic request/response models
│   ├── config.py                # .env loading + hot-reload
│   ├── services/
│   │   ├── base.py              # Abstract NotificationService + ServiceRegistry
│   │   ├── twilio_sms.py        # SMS plugin
│   │   ├── twilio_whatsapp.py   # WhatsApp plugin
│   │   └── email_smtp.py        # Email plugin
│   ├── api/
│   │   ├── members.py           # CRUD + upcoming events
│   │   ├── notifications.py     # Preview, send, pause
│   │   ├── logs.py              # History + retry
│   │   └── settings.py          # Timing, credentials, import/export
│   ├── utils/
│   │   ├── phone.py             # E.164 normalization
│   │   ├── messaging.py         # Template rendering + defaults
│   │   ├── sender.py            # Core send flow (state check → send → log)
│   │   └── migration.py         # JSON import/export
│   └── static/
│       ├── index.html
│       ├── style.css
│       └── app.js
├── tests/
│   ├── conftest.py              # Fixtures: in-memory DB, mock services, test client
│   ├── test_config.py
│   ├── test_database.py
│   ├── test_phone.py
│   ├── test_messaging.py
│   ├── test_services.py
│   ├── test_sender.py
│   ├── test_scheduler.py
│   ├── test_api_members.py
│   ├── test_api_notifications.py
│   ├── test_api_logs.py
│   ├── test_api_settings.py
│   └── test_migration.py
├── data/
│   └── exports/                 # Created at runtime
├── .env.example
├── .gitignore
├── requirements.txt
├── pytest.ini
└── systemd/
    └── family-notifier.service
```

---

## Task 1: Project Scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `pytest.ini`
- Create all directories in the file map above

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p app/services app/api app/utils app/static tests data/exports systemd
touch app/__init__.py app/services/__init__.py app/api/__init__.py app/utils/__init__.py
```

- [ ] **Step 2: Create `requirements.txt`**

```
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
apscheduler>=3.10.0,<4
twilio>=9.0.0
python-dotenv>=1.0.0
httpx>=0.27.0
pytest>=8.0.0
pytest-asyncio>=0.23.0
```

- [ ] **Step 3: Create `.env.example`**

```
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_FROM_NUMBER=+18772539457
TWILIO_WHATSAPP_NUMBER=+14155238886
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_ADDRESS=your@gmail.com
```

- [ ] **Step 4: Create `.gitignore`**

```
.env
data/family.db
data/exports/
__pycache__/
*.pyc
.pytest_cache/
```

- [ ] **Step 5: Create `pytest.ini`**

```ini
[pytest]
testpaths = tests
asyncio_mode = auto
```

- [ ] **Step 6: Install dependencies**

```bash
pip install -r requirements.txt
```

Expected: all packages install without error.

- [ ] **Step 7: Commit**

```bash
git init
git add requirements.txt .env.example .gitignore pytest.ini
git commit -m "feat: project scaffolding"
```

---

## Task 2: Config Loading

**Files:**
- Create: `app/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_config.py
import os, pytest
from app.config import get_config, hot_reload

def test_config_loads_from_env(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("TWILIO_ACCOUNT_SID=ACtest123\nTWILIO_AUTH_TOKEN=token123\n")
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "ACtest123")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "token123")
    cfg = get_config()
    assert cfg.twilio_account_sid == "ACtest123"

def test_config_missing_optional_fields_are_none(monkeypatch):
    monkeypatch.delenv("SMTP_HOST", raising=False)
    cfg = get_config()
    assert cfg.smtp_host is None
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
pytest tests/test_config.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.config'`

- [ ] **Step 3: Implement `app/config.py`**

```python
import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

@dataclass
class Config:
    twilio_account_sid: Optional[str]
    twilio_auth_token: Optional[str]
    twilio_from_number: Optional[str]
    twilio_whatsapp_number: Optional[str]
    smtp_host: Optional[str]
    smtp_port: int
    smtp_username: Optional[str]
    smtp_password: Optional[str]
    smtp_from_address: Optional[str]

_config: Optional[Config] = None

def get_config() -> Config:
    global _config
    if _config is None:
        hot_reload()
    return _config

def hot_reload():
    global _config
    load_dotenv(override=True)
    _config = Config(
        twilio_account_sid=os.getenv("TWILIO_ACCOUNT_SID"),
        twilio_auth_token=os.getenv("TWILIO_AUTH_TOKEN"),
        twilio_from_number=os.getenv("TWILIO_FROM_NUMBER"),
        twilio_whatsapp_number=os.getenv("TWILIO_WHATSAPP_NUMBER"),
        smtp_host=os.getenv("SMTP_HOST"),
        smtp_port=int(os.getenv("SMTP_PORT", "587")),
        smtp_username=os.getenv("SMTP_USERNAME"),
        smtp_password=os.getenv("SMTP_PASSWORD"),
        smtp_from_address=os.getenv("SMTP_FROM_ADDRESS"),
    )
```

- [ ] **Step 4: Run test — expect PASS**

```bash
pytest tests/test_config.py -v
```

- [ ] **Step 5: Commit**

```bash
git add app/config.py tests/test_config.py
git commit -m "feat: config loading from .env with hot-reload"
```

---

## Task 3: Database Setup

**Files:**
- Create: `app/database.py`
- Create: `tests/test_database.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_database.py
import sqlite3, pytest
from app.database import create_tables, seed_settings, get_connection

def test_tables_created(tmp_path):
    db_path = str(tmp_path / "test.db")
    conn = sqlite3.connect(db_path)
    create_tables(conn)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert {"people", "notification_state", "notification_log", "settings"} <= tables
    conn.close()

def test_notification_state_unique_constraint(tmp_path):
    db_path = str(tmp_path / "test.db")
    conn = sqlite3.connect(db_path)
    create_tables(conn)
    conn.execute("INSERT INTO people (name, birthday) VALUES ('Test', '01-01')")
    conn.execute("INSERT INTO notification_state (person_id, event_type, trigger_type, channel, year_sent) VALUES (1,'birthday','same_day','sms',2026)")
    conn.commit()
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO notification_state (person_id, event_type, trigger_type, channel, year_sent) VALUES (1,'birthday','same_day','sms',2026)")
        conn.commit()
    conn.close()

def test_seed_settings_inserts_defaults(tmp_path):
    db_path = str(tmp_path / "test.db")
    conn = sqlite3.connect(db_path)
    create_tables(conn)
    seed_settings(conn)
    row = conn.execute("SELECT value FROM settings WHERE key='advance_days_week'").fetchone()
    assert row[0] == "7"
    conn.close()
```

- [ ] **Step 2: Run — expect FAIL**

```bash
pytest tests/test_database.py -v
```

- [ ] **Step 3: Implement `app/database.py`**

```python
import sqlite3
from typing import Optional

DB_PATH = "data/family.db"

def get_connection(path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def create_tables(conn: sqlite3.Connection):
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS people (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT,
        email TEXT,
        whatsapp TEXT,
        birthday TEXT NOT NULL,
        birth_year INTEGER,
        married BOOLEAN DEFAULT 0,
        spouse_name TEXT,
        anniversary TEXT,
        anniversary_year INTEGER,
        custom_birthday_message TEXT DEFAULT '',
        custom_anniversary_message TEXT DEFAULT '',
        notifications_paused BOOLEAN DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS notification_state (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        person_id INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE,
        event_type TEXT NOT NULL,
        trigger_type TEXT NOT NULL,
        channel TEXT NOT NULL,
        year_sent INTEGER NOT NULL,
        sent_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(person_id, event_type, trigger_type, channel, year_sent)
    );
    CREATE TABLE IF NOT EXISTS notification_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        person_id INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE,
        event_type TEXT NOT NULL,
        trigger_type TEXT NOT NULL,
        channel TEXT NOT NULL,
        message_body TEXT NOT NULL,
        status TEXT NOT NULL,
        error_message TEXT,
        sent_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    """)
    conn.commit()

DEFAULTS = {
    "advance_days_week": "7",
    "advance_days_day": "1",
    "job1_time": "08:00",
    "job2_time": "12:00",
    "catch_up_hours": "6",
    "sms_enabled": "true",
    "whatsapp_enabled": "true",
    "email_enabled": "true",
}

def seed_settings(conn: sqlite3.Connection):
    for key, value in DEFAULTS.items():
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()

def init_db(path: str = DB_PATH):
    import os
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = get_connection(path)
    create_tables(conn)
    seed_settings(conn)
    return conn
```

- [ ] **Step 4: Run — expect PASS**

```bash
pytest tests/test_database.py -v
```

- [ ] **Step 5: Commit**

```bash
git add app/database.py tests/test_database.py
git commit -m "feat: SQLite schema with all 4 tables and default settings"
```

---

## Task 4: Phone Utility

**Files:**
- Create: `app/utils/phone.py`
- Create: `tests/test_phone.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_phone.py
from app.utils.phone import normalize_phone

def test_10_digit_us_number():
    assert normalize_phone("7188790062") == "+17188790062"

def test_already_e164():
    assert normalize_phone("+17188790062") == "+17188790062"

def test_with_dashes():
    assert normalize_phone("718-879-0062") == "+17188790062"

def test_with_parens():
    assert normalize_phone("(718) 879-0062") == "+17188790062"

def test_none_returns_none():
    assert normalize_phone(None) is None

def test_empty_returns_none():
    assert normalize_phone("") is None
```

- [ ] **Step 2: Run — expect FAIL**

```bash
pytest tests/test_phone.py -v
```

- [ ] **Step 3: Implement `app/utils/phone.py`**

```python
import re
from typing import Optional

def normalize_phone(phone: Optional[str]) -> Optional[str]:
    if not phone:
        return None
    digits = re.sub(r"\D", "", phone)
    if not digits:
        return None
    if phone.startswith("+"):
        return "+" + digits
    if len(digits) == 10:
        return "+1" + digits
    if len(digits) == 11 and digits.startswith("1"):
        return "+" + digits
    return "+" + digits
```

- [ ] **Step 4: Run — expect PASS**

```bash
pytest tests/test_phone.py -v
```

- [ ] **Step 5: Commit**

```bash
git add app/utils/phone.py tests/test_phone.py
git commit -m "feat: E.164 phone number normalization"
```

---

## Task 5: Message Template Utility

**Files:**
- Create: `app/utils/messaging.py`
- Create: `tests/test_messaging.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_messaging.py
import datetime
from app.utils.messaging import render_message, get_default_message

def test_render_name_variable():
    result = render_message("Happy Birthday {name}!", {"name": "John"}, days=0)
    assert result == "Happy Birthday John!"

def test_render_age_variable():
    birth_year = datetime.date.today().year - 40
    result = render_message("{name} is {age}!", {"name": "John", "birth_year": birth_year}, days=0)
    assert result == "John is 40!"

def test_render_missing_birth_year_omits_age():
    result = render_message("{name} is {age}!", {"name": "John", "birth_year": None}, days=0)
    assert "{age}" not in result

def test_render_days_variable():
    result = render_message("In {days} days!", {}, days=7)
    assert result == "In 7 days!"

def test_render_years_married():
    anniversary_year = datetime.date.today().year - 10
    result = render_message("{years_married} years!", {"anniversary_year": anniversary_year}, days=0)
    assert result == "10 years!"

def test_default_birthday_advance():
    msg = get_default_message("birthday", "7_day", for_person=False)
    assert "{name}" in msg and "{days}" in msg

def test_default_birthday_same_day():
    msg = get_default_message("birthday", "same_day", for_person=True)
    assert "{name}" in msg
    assert "Happy Birthday" in msg

def test_default_anniversary_advance():
    msg = get_default_message("anniversary", "1_day", for_person=False)
    assert "{name}" in msg and "{spouse}" in msg

def test_default_anniversary_same_day():
    msg = get_default_message("anniversary", "same_day", for_person=True)
    assert "Anniversary" in msg
```

- [ ] **Step 2: Run — expect FAIL**

```bash
pytest tests/test_messaging.py -v
```

- [ ] **Step 3: Implement `app/utils/messaging.py`**

```python
import datetime
from typing import Optional

DEFAULTS = {
    ("birthday", "advance", False):    "NoorFamily Reminder: {name}'s birthday is in {days} day(s)! Don't forget to wish them!",
    ("birthday", "same_day", True):    "Happy Birthday, {name}! Wishing you joy and happiness today!",
    ("anniversary", "advance", False): "NoorFamily Reminder: {name} & {spouse}'s anniversary is in {days} day(s)!",
    ("anniversary", "same_day", True): "Happy Anniversary, {name} & {spouse}! Wishing you many more years of happiness together!",
}

def get_default_message(event_type: str, trigger_type: str, for_person: bool) -> str:
    category = "same_day" if trigger_type == "same_day" else "advance"
    return DEFAULTS.get((event_type, category, for_person), "")

def render_message(template: str, person: dict, days: int) -> str:
    today = datetime.date.today()
    variables = {
        "name": person.get("name", ""),
        "spouse": person.get("spouse_name", ""),
        "day_of_week": today.strftime("%A"),
        "days": str(days),
    }
    birth_year = person.get("birth_year")
    if birth_year:
        variables["age"] = str(today.year - int(birth_year))
    else:
        template = template.replace("{age}", "")

    ann_year = person.get("anniversary_year")
    if ann_year:
        variables["years_married"] = str(today.year - int(ann_year))
    else:
        template = template.replace("{years_married}", "")

    for key, value in variables.items():
        template = template.replace("{" + key + "}", value)
    return template
```

- [ ] **Step 4: Run — expect PASS**

```bash
pytest tests/test_messaging.py -v
```

- [ ] **Step 5: Commit**

```bash
git add app/utils/messaging.py tests/test_messaging.py
git commit -m "feat: message template rendering with variable substitution"
```

---

## Task 6: Notification Plugin Base + Registry

**Files:**
- Create: `app/services/base.py`
- Create: `tests/test_services.py` (partial)

- [ ] **Step 1: Write failing test**

```python
# tests/test_services.py
from app.services.base import NotificationService, ServiceRegistry

class MockService(NotificationService):
    name = "mock"
    def send(self, person, message):
        if not person.get("phone"):
            return True
        self.sent.append((person, message))
        return True
    def health_check(self):
        return True

def test_registry_returns_enabled_services():
    svc = MockService()
    svc.enabled = True
    svc.sent = []
    registry = ServiceRegistry([svc])
    assert registry.get_enabled() == [svc]

def test_registry_excludes_disabled():
    svc = MockService()
    svc.enabled = False
    registry = ServiceRegistry([svc])
    assert registry.get_enabled() == []
```

- [ ] **Step 2: Run — expect FAIL**

```bash
pytest tests/test_services.py -v
```

- [ ] **Step 3: Implement `app/services/base.py`**

```python
from abc import ABC, abstractmethod
from typing import List

class NotificationService(ABC):
    name: str
    enabled: bool = True

    @abstractmethod
    def send(self, person: dict, message: str) -> bool:
        ...

    @abstractmethod
    def health_check(self) -> bool:
        ...

class ServiceRegistry:
    def __init__(self, services: List[NotificationService]):
        self._services = services

    def get_enabled(self) -> List[NotificationService]:
        return [s for s in self._services if s.enabled]

    def get_all(self) -> List[NotificationService]:
        return self._services
```

- [ ] **Step 4: Run — expect PASS**

```bash
pytest tests/test_services.py -v
```

- [ ] **Step 5: Commit**

```bash
git add app/services/base.py tests/test_services.py
git commit -m "feat: notification service plugin interface and registry"
```

---

## Task 7: Twilio SMS Plugin

**Files:**
- Create: `app/services/twilio_sms.py`
- Modify: `tests/test_services.py`

- [ ] **Step 1: Add failing tests to `tests/test_services.py`**

```python
from unittest.mock import MagicMock, patch
from app.services.twilio_sms import TwilioSMSService

def test_sms_sends_to_phone():
    with patch("app.services.twilio_sms.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        svc = TwilioSMSService(account_sid="AC123", auth_token="tok", from_number="+10000000000")
        person = {"name": "John", "phone": "+17188790062"}
        result = svc.send(person, "Happy Birthday John!")
        assert result is True
        mock_client.messages.create.assert_called_once()
        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["to"] == "+17188790062"

def test_sms_skips_person_with_no_phone():
    with patch("app.services.twilio_sms.Client"):
        svc = TwilioSMSService(account_sid="AC123", auth_token="tok", from_number="+10000000000")
        person = {"name": "John", "phone": None}
        result = svc.send(person, "msg")
        assert result is True  # skip, not failure

def test_sms_returns_false_on_twilio_error():
    with patch("app.services.twilio_sms.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("Twilio error")
        mock_client_cls.return_value = mock_client
        svc = TwilioSMSService(account_sid="AC123", auth_token="tok", from_number="+10000000000")
        person = {"name": "John", "phone": "+17188790062"}
        result = svc.send(person, "msg")
        assert result is False
```

- [ ] **Step 2: Run — expect FAIL**

```bash
pytest tests/test_services.py::test_sms_sends_to_phone -v
```

- [ ] **Step 3: Implement `app/services/twilio_sms.py`**

```python
from twilio.rest import Client
from app.services.base import NotificationService

class TwilioSMSService(NotificationService):
    name = "sms"

    def __init__(self, account_sid: str, auth_token: str, from_number: str):
        self._client = Client(account_sid, auth_token)
        self._from = from_number
        self.enabled = True

    def send(self, person: dict, message: str) -> bool:
        recipient = person.get("phone")
        if not recipient:
            return True
        try:
            self._client.messages.create(to=recipient, from_=self._from, body=message)
            return True
        except Exception as e:
            print(f"SMS send failed for {person.get('name')}: {e}")
            return False

    def health_check(self) -> bool:
        try:
            self._client.api.accounts(self._client.account_sid).fetch()
            return True
        except Exception:
            return False
```

- [ ] **Step 4: Run — expect PASS**

```bash
pytest tests/test_services.py -v
```

- [ ] **Step 5: Commit**

```bash
git add app/services/twilio_sms.py tests/test_services.py
git commit -m "feat: Twilio SMS notification plugin"
```

---

## Task 8: Twilio WhatsApp Plugin

**Files:**
- Create: `app/services/twilio_whatsapp.py`
- Modify: `tests/test_services.py`

- [ ] **Step 1: Add failing tests**

```python
from app.services.twilio_whatsapp import TwilioWhatsAppService

def test_whatsapp_uses_whatsapp_field_when_set():
    with patch("app.services.twilio_whatsapp.Client") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        svc = TwilioWhatsAppService("AC123", "tok", "whatsapp:+14155238886")
        person = {"name": "John", "phone": "+17188790062", "whatsapp": "+19998887777"}
        svc.send(person, "msg")
        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["to"] == "whatsapp:+19998887777"

def test_whatsapp_falls_back_to_phone():
    with patch("app.services.twilio_whatsapp.Client") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        svc = TwilioWhatsAppService("AC123", "tok", "whatsapp:+14155238886")
        person = {"name": "John", "phone": "+17188790062", "whatsapp": None}
        svc.send(person, "msg")
        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["to"] == "whatsapp:+17188790062"
```

- [ ] **Step 2: Run — expect FAIL**

```bash
pytest tests/test_services.py::test_whatsapp_uses_whatsapp_field_when_set -v
```

- [ ] **Step 3: Implement `app/services/twilio_whatsapp.py`**

```python
from twilio.rest import Client
from app.services.base import NotificationService

class TwilioWhatsAppService(NotificationService):
    name = "whatsapp"

    def __init__(self, account_sid: str, auth_token: str, from_number: str):
        self._client = Client(account_sid, auth_token)
        self._from = from_number
        self.enabled = True

    def send(self, person: dict, message: str) -> bool:
        number = person.get("whatsapp") or person.get("phone")
        if not number:
            return True
        to = f"whatsapp:{number}"
        try:
            self._client.messages.create(to=to, from_=self._from, body=message)
            return True
        except Exception as e:
            print(f"WhatsApp send failed for {person.get('name')}: {e}")
            return False

    def health_check(self) -> bool:
        try:
            self._client.api.accounts(self._client.account_sid).fetch()
            return True
        except Exception:
            return False
```

- [ ] **Step 4: Run — expect PASS**

```bash
pytest tests/test_services.py -v
```

- [ ] **Step 5: Commit**

```bash
git add app/services/twilio_whatsapp.py tests/test_services.py
git commit -m "feat: Twilio WhatsApp notification plugin"
```

---

## Task 9: Email SMTP Plugin

**Files:**
- Create: `app/services/email_smtp.py`
- Modify: `tests/test_services.py`

- [ ] **Step 1: Add failing tests**

```python
from app.services.email_smtp import EmailService

def test_email_sends_to_email_field():
    with patch("app.services.email_smtp.smtplib.SMTP") as mock_smtp_cls:
        mock_smtp = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_smtp)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
        svc = EmailService("smtp.gmail.com", 587, "user@test.com", "pass", "user@test.com")
        person = {"name": "John", "email": "john@example.com"}
        result = svc.send(person, "Happy Birthday!")
        assert result is True
        mock_smtp.sendmail.assert_called_once()

def test_email_skips_person_with_no_email():
    svc = EmailService("smtp.gmail.com", 587, "user@test.com", "pass", "user@test.com")
    person = {"name": "John", "email": None}
    result = svc.send(person, "msg")
    assert result is True
```

- [ ] **Step 2: Run — expect FAIL**

```bash
pytest tests/test_services.py::test_email_sends_to_email_field -v
```

- [ ] **Step 3: Implement `app/services/email_smtp.py`**

```python
import smtplib
from email.mime.text import MIMEText
from app.services.base import NotificationService

class EmailService(NotificationService):
    name = "email"

    def __init__(self, host: str, port: int, username: str, password: str, from_address: str):
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._from = from_address
        self.enabled = True

    def send(self, person: dict, message: str) -> bool:
        recipient = person.get("email")
        if not recipient:
            return True
        try:
            msg = MIMEText(message)
            msg["Subject"] = f"NoorFamily — {message[:40]}..."
            msg["From"] = self._from
            msg["To"] = recipient
            with smtplib.SMTP(self._host, self._port) as server:
                server.starttls()
                server.login(self._username, self._password)
                server.sendmail(self._from, recipient, msg.as_string())
            return True
        except Exception as e:
            print(f"Email send failed for {person.get('name')}: {e}")
            return False

    def health_check(self) -> bool:
        try:
            with smtplib.SMTP(self._host, self._port, timeout=5) as server:
                server.ehlo()
            return True
        except Exception:
            return False
```

- [ ] **Step 4: Run — expect PASS**

```bash
pytest tests/test_services.py -v
```

- [ ] **Step 5: Commit**

```bash
git add app/services/email_smtp.py tests/test_services.py
git commit -m "feat: SMTP email notification plugin"
```

---

## Task 10: Notification Sender Core

**Files:**
- Create: `app/utils/sender.py`
- Create: `tests/test_sender.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create `tests/conftest.py`**

```python
import sqlite3
import pytest
from app.database import create_tables, seed_settings

@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    create_tables(conn)
    seed_settings(conn)
    conn.execute("INSERT INTO people (name, phone, email, birthday) VALUES ('John', '+17188790062', 'john@test.com', '01-28')")
    conn.commit()
    yield conn
    conn.close()

@pytest.fixture
def client(tmp_path):
    import sqlite3 as _sqlite3
    db_path = str(tmp_path / "test.db")
    conn = _sqlite3.connect(db_path)
    create_tables(conn)
    seed_settings(conn)
    conn.execute("INSERT INTO people (name, phone, email, birthday) VALUES ('John', '+17188790062', 'john@test.com', '01-28')")
    conn.commit()
    conn.close()
    from app.main import create_app
    from fastapi.testclient import TestClient
    return TestClient(create_app(db_path=db_path))

@pytest.fixture
def mock_sms_service():
    from app.services.base import NotificationService
    class MockSMS(NotificationService):
        name = "sms"
        enabled = True
        calls = []
        def send(self, person, message):
            self.calls.append((person["name"], message))
            return True
        def health_check(self):
            return True
    return MockSMS()
```

- [ ] **Step 2: Write failing tests**

```python
# tests/test_sender.py
import datetime
from app.utils.sender import execute_send

def test_send_writes_log_on_success(db, mock_sms_service):
    person = dict(db.execute("SELECT * FROM people WHERE id=1").fetchone())
    execute_send(db, person, "birthday", "same_day", "Happy Birthday!", [mock_sms_service], write_state=True)
    log = db.execute("SELECT * FROM notification_log WHERE person_id=1").fetchone()
    assert log["status"] == "sent"
    assert log["channel"] == "sms"

def test_send_writes_state_on_success(db, mock_sms_service):
    person = dict(db.execute("SELECT * FROM people WHERE id=1").fetchone())
    execute_send(db, person, "birthday", "same_day", "Happy Birthday!", [mock_sms_service], write_state=True)
    state = db.execute("SELECT * FROM notification_state WHERE person_id=1").fetchone()
    assert state is not None
    assert state["channel"] == "sms"

def test_send_skips_if_state_exists(db, mock_sms_service):
    year = datetime.date.today().year
    db.execute("INSERT INTO notification_state (person_id, event_type, trigger_type, channel, year_sent) VALUES (1,'birthday','same_day','sms',?)", (year,))
    db.commit()
    person = dict(db.execute("SELECT * FROM people WHERE id=1").fetchone())
    execute_send(db, person, "birthday", "same_day", "msg", [mock_sms_service], write_state=True)
    assert len(mock_sms_service.calls) == 0

def test_failed_send_writes_log_no_state(db):
    from app.services.base import NotificationService
    class FailSMS(NotificationService):
        name = "sms"
        enabled = True
        def send(self, person, message): return False
        def health_check(self): return False
    person = dict(db.execute("SELECT * FROM people WHERE id=1").fetchone())
    execute_send(db, person, "birthday", "same_day", "msg", [FailSMS()], write_state=True)
    log = db.execute("SELECT * FROM notification_log WHERE person_id=1").fetchone()
    assert log["status"] == "failed"
    state = db.execute("SELECT * FROM notification_state WHERE person_id=1").fetchone()
    assert state is None
```

- [ ] **Step 3: Run — expect FAIL**

```bash
pytest tests/test_sender.py -v
```

- [ ] **Step 4: Implement `app/utils/sender.py`**

```python
import datetime
import sqlite3
from typing import List
from app.services.base import NotificationService

def already_sent(db: sqlite3.Connection, person_id: int, event_type: str, trigger_type: str, channel: str) -> bool:
    year = datetime.date.today().year
    row = db.execute(
        "SELECT 1 FROM notification_state WHERE person_id=? AND event_type=? AND trigger_type=? AND channel=? AND year_sent=?",
        (person_id, event_type, trigger_type, channel, year)
    ).fetchone()
    return row is not None

def execute_send(
    db: sqlite3.Connection,
    person: dict,
    event_type: str,
    trigger_type: str,
    message: str,
    services: List[NotificationService],
    write_state: bool = True,
):
    year = datetime.date.today().year
    for service in services:
        if not service.enabled:
            continue
        if write_state and already_sent(db, person["id"], event_type, trigger_type, service.name):
            continue
        success = service.send(person, message)
        db.execute(
            "INSERT INTO notification_log (person_id, event_type, trigger_type, channel, message_body, status) VALUES (?,?,?,?,?,?)",
            (person["id"], event_type, trigger_type, service.name, message, "sent" if success else "failed")
        )
        if success and write_state:
            try:
                db.execute(
                    "INSERT INTO notification_state (person_id, event_type, trigger_type, channel, year_sent) VALUES (?,?,?,?,?)",
                    (person["id"], event_type, trigger_type, service.name, year)
                )
            except Exception:
                pass
        db.commit()
```

- [ ] **Step 5: Run — expect PASS**

```bash
pytest tests/test_sender.py -v
```

- [ ] **Step 6: Commit**

```bash
git add app/utils/sender.py tests/test_sender.py tests/conftest.py
git commit -m "feat: core notification send flow with state and log tracking"
```

---

## Task 11: Scheduler Jobs

**Files:**
- Create: `app/scheduler.py`
- Create: `tests/test_scheduler.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_scheduler.py
import datetime, sqlite3
from unittest.mock import MagicMock, patch
from app.scheduler import run_advance_reminders, run_day_of_wishes

def make_db():
    from app.database import create_tables, seed_settings
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    create_tables(conn)
    seed_settings(conn)
    return conn

def test_advance_reminder_sends_to_others():
    db = make_db()
    today = datetime.date.today()
    in_7 = (today + datetime.timedelta(days=7)).strftime("%m-%d")
    db.execute("INSERT INTO people (name, phone, birthday) VALUES ('Birthday Person', '+10000000001', ?)", (in_7,))
    db.execute("INSERT INTO people (name, phone, birthday) VALUES ('Other Family', '+10000000002', '06-15')")
    db.commit()
    mock_service = MagicMock()
    mock_service.name = "sms"
    mock_service.enabled = True
    mock_service.send.return_value = True
    with patch("app.scheduler.get_services", return_value=[mock_service]):
        with patch("app.scheduler.get_db", return_value=db):
            run_advance_reminders()
    assert mock_service.send.call_count == 1
    call_args = mock_service.send.call_args[0]
    assert call_args[0]["name"] == "Other Family"

def test_day_of_wishes_sends_to_person():
    db = make_db()
    today = datetime.date.today().strftime("%m-%d")
    db.execute("INSERT INTO people (name, phone, birthday) VALUES ('Birthday Person', '+10000000001', ?)", (today,))
    db.execute("INSERT INTO people (name, phone, birthday) VALUES ('Other Family', '+10000000002', '06-15')")
    db.commit()
    mock_service = MagicMock()
    mock_service.name = "sms"
    mock_service.enabled = True
    mock_service.send.return_value = True
    with patch("app.scheduler.get_services", return_value=[mock_service]):
        with patch("app.scheduler.get_db", return_value=db):
            run_day_of_wishes()
    assert mock_service.send.call_count == 1
    call_args = mock_service.send.call_args[0]
    assert call_args[0]["name"] == "Birthday Person"
```

- [ ] **Step 2: Run — expect FAIL**

```bash
pytest tests/test_scheduler.py -v
```

- [ ] **Step 3: Implement `app/scheduler.py`**

```python
import datetime
import sqlite3
from apscheduler.schedulers.background import BackgroundScheduler
from app.database import get_connection
from app.utils.messaging import render_message, get_default_message
from app.utils.sender import execute_send

_scheduler = None
_services = []
_db_path = "data/family.db"

def get_db():
    return get_connection(_db_path)

def get_services():
    return _services

def days_until(date_str: str) -> int:
    today = datetime.date.today()
    month, day = map(int, date_str.split("-"))
    target = datetime.date(today.year, month, day)
    if target < today:
        target = datetime.date(today.year + 1, month, day)
    return (target - today).days

def _get_setting(db, key: str, default: str) -> str:
    row = db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row[0] if row else default

def run_advance_reminders():
    db = get_db()
    services = get_services()
    people = [dict(r) for r in db.execute("SELECT * FROM people WHERE notifications_paused=0").fetchall()]
    week_days = int(_get_setting(db, "advance_days_week", "7"))
    day_days = int(_get_setting(db, "advance_days_day", "1"))

    for person in people:
        for days_ahead, trigger_type in [(week_days, "7_day"), (day_days, "1_day")]:
            # Birthday
            if person.get("birthday"):
                if days_until(person["birthday"]) == days_ahead:
                    template = person.get("custom_birthday_message") or get_default_message("birthday", trigger_type, False)
                    message = render_message(template, person, days=days_ahead)
                    recipients = [p for p in people if p["id"] != person["id"]]
                    for recipient in recipients:
                        execute_send(db, recipient, "birthday", trigger_type, message, services, write_state=True)
            # Anniversary
            if person.get("married") and person.get("anniversary"):
                if days_until(person["anniversary"]) == days_ahead:
                    template = person.get("custom_anniversary_message") or get_default_message("anniversary", trigger_type, False)
                    message = render_message(template, person, days=days_ahead)
                    recipients = [p for p in people if p["id"] != person["id"]]
                    for recipient in recipients:
                        execute_send(db, recipient, "anniversary", trigger_type, message, services, write_state=True)
    db.close()

def run_day_of_wishes():
    db = get_db()
    services = get_services()
    people = [dict(r) for r in db.execute("SELECT * FROM people WHERE notifications_paused=0").fetchall()]

    for person in people:
        if person.get("birthday") and days_until(person["birthday"]) == 0:
            template = person.get("custom_birthday_message") or get_default_message("birthday", "same_day", True)
            message = render_message(template, person, days=0)
            execute_send(db, person, "birthday", "same_day", message, services, write_state=True)
        if person.get("married") and person.get("anniversary") and days_until(person["anniversary"]) == 0:
            template = person.get("custom_anniversary_message") or get_default_message("anniversary", "same_day", True)
            message = render_message(template, person, days=0)
            execute_send(db, person, "anniversary", "same_day", message, services, write_state=True)
    db.close()

def setup_scheduler(services_list: list, db_path: str = "data/family.db"):
    global _scheduler, _services, _db_path
    _services = services_list
    _db_path = db_path

    db = get_connection(db_path)
    job1_time = _get_setting(db, "job1_time", "08:00")
    job2_time = _get_setting(db, "job2_time", "12:00")
    catch_up_hours = int(_get_setting(db, "catch_up_hours", "6"))
    db.close()

    j1_hour, j1_min = map(int, job1_time.split(":"))
    j2_hour, j2_min = map(int, job2_time.split(":"))

    _scheduler = BackgroundScheduler()
    _scheduler.add_job(run_advance_reminders, "cron", hour=j1_hour, minute=j1_min, id="advance_reminders")
    _scheduler.add_job(run_day_of_wishes, "cron", hour=j2_hour, minute=j2_min, id="day_of_wishes",
                       misfire_grace_time=catch_up_hours * 3600)
    _scheduler.start()

def stop_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown()
```

- [ ] **Step 4: Run — expect PASS**

```bash
pytest tests/test_scheduler.py -v
```

- [ ] **Step 5: Commit**

```bash
git add app/scheduler.py tests/test_scheduler.py
git commit -m "feat: APScheduler jobs for advance reminders and day-of wishes"
```

---

## Task 12: Members API

**Files:**
- Create: `app/api/members.py`
- Create: `tests/test_api_members.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_api_members.py
import pytest
from fastapi.testclient import TestClient

@pytest.fixture
def client(tmp_path):
    import sqlite3
    from app.database import create_tables, seed_settings
    db_path = str(tmp_path / "test.db")
    conn = sqlite3.connect(db_path)
    create_tables(conn)
    seed_settings(conn)
    conn.close()
    from app.main import create_app
    app = create_app(db_path=db_path)
    return TestClient(app)

def test_list_members_empty(client):
    r = client.get("/api/members")
    assert r.status_code == 200
    assert r.json() == []

def test_create_member(client):
    r = client.post("/api/members", json={"name": "John", "birthday": "01-28", "phone": "7188790062"})
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "John"
    assert data["phone"] == "+17188790062"

def test_update_member(client):
    r = client.post("/api/members", json={"name": "John", "birthday": "01-28"})
    mid = r.json()["id"]
    r2 = client.put(f"/api/members/{mid}", json={"name": "John Updated", "birthday": "01-28"})
    assert r2.status_code == 200
    assert r2.json()["name"] == "John Updated"

def test_delete_member(client):
    r = client.post("/api/members", json={"name": "John", "birthday": "01-28"})
    mid = r.json()["id"]
    r2 = client.delete(f"/api/members/{mid}")
    assert r2.status_code == 204
    assert client.get("/api/members").json() == []

def test_upcoming_events(client):
    import datetime
    in_5 = (datetime.date.today() + datetime.timedelta(days=5)).strftime("%m-%d")
    client.post("/api/members", json={"name": "John", "birthday": in_5})
    r = client.get("/api/members/upcoming")
    assert r.status_code == 200
    events = r.json()
    assert any(e["name"] == "John" for e in events)
```

- [ ] **Step 2: Run — expect FAIL**

```bash
pytest tests/test_api_members.py -v
```

- [ ] **Step 3: Create `app/models.py`**

```python
from pydantic import BaseModel
from typing import Optional

class PersonCreate(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    whatsapp: Optional[str] = None
    birthday: str
    birth_year: Optional[int] = None
    married: bool = False
    spouse_name: Optional[str] = None
    anniversary: Optional[str] = None
    anniversary_year: Optional[int] = None
    custom_birthday_message: str = ""
    custom_anniversary_message: str = ""
    notifications_paused: bool = False

class PersonUpdate(PersonCreate):
    pass

class PersonResponse(PersonCreate):
    id: int
    created_at: str
    updated_at: str
```

- [ ] **Step 4: Implement `app/api/members.py`**

```python
import datetime
import sqlite3
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from app.models import PersonCreate, PersonUpdate
from app.utils.phone import normalize_phone

router = APIRouter(prefix="/api/members", tags=["members"])

def get_db_dep(db_path: str = "data/family.db"):
    from app.database import get_connection
    conn = get_connection(db_path)
    try:
        yield conn
    finally:
        conn.close()

@router.get("")
def list_members(db: sqlite3.Connection = Depends(get_db_dep)):
    rows = db.execute("SELECT * FROM people ORDER BY name").fetchall()
    return [dict(r) for r in rows]

@router.post("", status_code=201)
def create_member(person: PersonCreate, db: sqlite3.Connection = Depends(get_db_dep)):
    data = person.dict()
    data["phone"] = normalize_phone(data.get("phone"))
    data["whatsapp"] = normalize_phone(data.get("whatsapp"))
    if data["whatsapp"] == data["phone"]:
        data["whatsapp"] = None
    cursor = db.execute(
        """INSERT INTO people (name,phone,email,whatsapp,birthday,birth_year,married,spouse_name,
           anniversary,anniversary_year,custom_birthday_message,custom_anniversary_message,notifications_paused)
           VALUES (:name,:phone,:email,:whatsapp,:birthday,:birth_year,:married,:spouse_name,
           :anniversary,:anniversary_year,:custom_birthday_message,:custom_anniversary_message,:notifications_paused)""",
        data
    )
    db.commit()
    row = db.execute("SELECT * FROM people WHERE id=?", (cursor.lastrowid,)).fetchone()
    return dict(row)

@router.put("/{person_id}")
def update_member(person_id: int, person: PersonUpdate, db: sqlite3.Connection = Depends(get_db_dep)):
    existing = db.execute("SELECT id FROM people WHERE id=?", (person_id,)).fetchone()
    if not existing:
        raise HTTPException(404, "Person not found")
    data = person.dict()
    data["phone"] = normalize_phone(data.get("phone"))
    data["whatsapp"] = normalize_phone(data.get("whatsapp"))
    if data["whatsapp"] == data["phone"]:
        data["whatsapp"] = None
    data["id"] = person_id
    data["updated_at"] = datetime.datetime.utcnow().isoformat()
    db.execute(
        """UPDATE people SET name=:name,phone=:phone,email=:email,whatsapp=:whatsapp,birthday=:birthday,
           birth_year=:birth_year,married=:married,spouse_name=:spouse_name,anniversary=:anniversary,
           anniversary_year=:anniversary_year,custom_birthday_message=:custom_birthday_message,
           custom_anniversary_message=:custom_anniversary_message,notifications_paused=:notifications_paused,
           updated_at=:updated_at WHERE id=:id""",
        data
    )
    db.commit()
    return dict(db.execute("SELECT * FROM people WHERE id=?", (person_id,)).fetchone())

@router.delete("/{person_id}", status_code=204)
def delete_member(person_id: int, db: sqlite3.Connection = Depends(get_db_dep)):
    db.execute("DELETE FROM people WHERE id=?", (person_id,))
    db.commit()

@router.get("/upcoming")
def upcoming_events(db: sqlite3.Connection = Depends(get_db_dep)):
    today = datetime.date.today()
    people = [dict(r) for r in db.execute("SELECT * FROM people WHERE notifications_paused=0").fetchall()]
    events = []
    for p in people:
        for event_type, date_str in [("birthday", p.get("birthday")), ("anniversary", p.get("anniversary") if p.get("married") else None)]:
            if not date_str:
                continue
            month, day = map(int, date_str.split("-"))
            target = datetime.date(today.year, month, day)
            if target < today:
                target = datetime.date(today.year + 1, month, day)
            days_away = (target - today).days
            if days_away <= 30:
                events.append({"id": p["id"], "name": p["name"], "event_type": event_type, "date": date_str, "days_away": days_away})
    return sorted(events, key=lambda x: x["days_away"])
```

- [ ] **Step 5: Create minimal `app/main.py` for tests**

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.api import members, notifications, logs, settings as settings_api

def create_app(db_path: str = "data/family.db") -> FastAPI:
    app = FastAPI(title="Family Notification System")
    app.include_router(members.router)
    return app

app = create_app()
```

- [ ] **Step 6: Run — expect PASS**

```bash
pytest tests/test_api_members.py -v
```

- [ ] **Step 7: Commit**

```bash
git add app/models.py app/api/members.py app/main.py tests/test_api_members.py
git commit -m "feat: members CRUD API with upcoming events"
```

---

## Task 13: Notifications, Logs, and Settings APIs

**Files:**
- Create: `app/api/notifications.py`
- Create: `app/api/logs.py`
- Create: `app/api/settings.py`
- Create: `tests/test_api_notifications.py`
- Create: `tests/test_api_logs.py`
- Create: `tests/test_api_settings.py`

- [ ] **Step 1: Write failing tests for notifications API**

```python
# tests/test_api_notifications.py
import pytest
from fastapi.testclient import TestClient

@pytest.fixture
def client_with_member(tmp_path):
    import sqlite3
    from app.database import create_tables, seed_settings
    db_path = str(tmp_path / "test.db")
    conn = sqlite3.connect(db_path)
    create_tables(conn); seed_settings(conn)
    conn.execute("INSERT INTO people (name,phone,birthday) VALUES ('John','+17188790062','01-28')")
    conn.commit(); conn.close()
    from app.main import create_app
    app = create_app(db_path=db_path)
    return TestClient(app)

def test_preview_renders_message(client_with_member):
    r = client_with_member.post("/api/notifications/preview", json={
        "person_id": 1, "event_type": "birthday", "trigger_type": "same_day"
    })
    assert r.status_code == 200
    data = r.json()
    assert "John" in data["sms"]

def test_pause_member(client_with_member):
    r = client_with_member.put("/api/members/1/pause", json={"paused": True})
    assert r.status_code == 200
    assert r.json()["notifications_paused"] is True
```

- [ ] **Step 2: Implement `app/api/notifications.py`**

```python
import sqlite3
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from app.utils.messaging import render_message, get_default_message
from app.utils.sender import execute_send

router = APIRouter(prefix="/api", tags=["notifications"])

class PreviewRequest(BaseModel):
    person_id: int
    event_type: str
    trigger_type: str

class SendRequest(BaseModel):
    person_id: int
    event_type: str
    trigger_type: str

class PauseRequest(BaseModel):
    paused: bool

def get_db_dep(db_path="data/family.db"):
    from app.database import get_connection
    conn = get_connection(db_path)
    try:
        yield conn
    finally:
        conn.close()

@router.post("/notifications/preview")
def preview(req: PreviewRequest, db: sqlite3.Connection = Depends(get_db_dep)):
    person = db.execute("SELECT * FROM people WHERE id=?", (req.person_id,)).fetchone()
    if not person:
        raise HTTPException(404, "Person not found")
    person = dict(person)
    for_person = req.trigger_type == "same_day"
    import datetime
    date_str = person["anniversary"] if req.event_type == "anniversary" and person.get("anniversary") else person["birthday"]
    month, day = map(int, date_str.split("-"))
    today = datetime.date.today()
    target = datetime.date(today.year, month, day)
    if target < today:
        target = datetime.date(today.year + 1, month, day)
    days = (target - today).days
    field = f"custom_{req.event_type}_message"
    template = person.get(field) or get_default_message(req.event_type, req.trigger_type, for_person)
    message = render_message(template, person, days=days)
    return {"sms": message, "whatsapp": message, "email": message}

@router.post("/notifications/send", status_code=202)
def send_now(req: SendRequest, db: sqlite3.Connection = Depends(get_db_dep)):
    from app.scheduler import get_services
    person = db.execute("SELECT * FROM people WHERE id=?", (req.person_id,)).fetchone()
    if not person:
        raise HTTPException(404, "Person not found")
    person = dict(person)
    for_person = req.trigger_type == "same_day"
    import datetime
    date_str = person["anniversary"] if req.event_type == "anniversary" and person.get("anniversary") else person["birthday"]
    month, day = map(int, date_str.split("-"))
    today = datetime.date.today()
    target = datetime.date(today.year, month, day)
    if target < today:
        target = datetime.date(today.year + 1, month, day)
    days = (target - today).days
    field = f"custom_{req.event_type}_message"
    template = person.get(field) or get_default_message(req.event_type, req.trigger_type, for_person)
    message = render_message(template, person, days=days)
    write_state = req.trigger_type == "same_day"
    execute_send(db, person, req.event_type, req.trigger_type, message, get_services(), write_state=write_state)
    return {"status": "dispatched"}

@router.put("/members/{person_id}/pause")
def pause_member(person_id: int, req: PauseRequest, db: sqlite3.Connection = Depends(get_db_dep)):
    db.execute("UPDATE people SET notifications_paused=? WHERE id=?", (1 if req.paused else 0, person_id))
    db.commit()
    row = db.execute("SELECT * FROM people WHERE id=?", (person_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Person not found")
    return dict(row)
```

- [ ] **Step 3: Implement `app/api/logs.py`**

```python
import sqlite3
from fastapi import APIRouter, Depends
from typing import Optional
from app.utils.sender import execute_send

router = APIRouter(prefix="/api/logs", tags=["logs"])

def get_db_dep(db_path="data/family.db"):
    from app.database import get_connection
    conn = get_connection(db_path)
    try:
        yield conn
    finally:
        conn.close()

@router.get("")
def list_logs(
    person_id: Optional[int] = None,
    channel: Optional[str] = None,
    event_type: Optional[str] = None,
    trigger_type: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: sqlite3.Connection = Depends(get_db_dep)
):
    query = "SELECT l.*, p.name as person_name FROM notification_log l JOIN people p ON l.person_id=p.id WHERE 1=1"
    params = []
    if person_id: query += " AND l.person_id=?"; params.append(person_id)
    if channel: query += " AND l.channel=?"; params.append(channel)
    if event_type: query += " AND l.event_type=?"; params.append(event_type)
    if trigger_type: query += " AND l.trigger_type=?"; params.append(trigger_type)
    if status: query += " AND l.status=?"; params.append(status)
    if date_from: query += " AND l.sent_at >= ?"; params.append(date_from)
    if date_to: query += " AND l.sent_at <= ?"; params.append(date_to)
    query += " ORDER BY l.sent_at DESC LIMIT 500"
    return [dict(r) for r in db.execute(query, params).fetchall()]

@router.post("/{log_id}/retry", status_code=202)
def retry_log(log_id: int, db: sqlite3.Connection = Depends(get_db_dep)):
    from app.scheduler import get_services
    log = db.execute("SELECT * FROM notification_log WHERE id=?", (log_id,)).fetchone()
    if not log or log["status"] != "failed":
        from fastapi import HTTPException
        raise HTTPException(404, "Failed log entry not found")
    person = dict(db.execute("SELECT * FROM people WHERE id=?", (log["person_id"],)).fetchone())
    services = [s for s in get_services() if s.name == log["channel"]]
    execute_send(db, person, log["event_type"], log["trigger_type"], log["message_body"], services, write_state=False)
    return {"status": "retried"}
```

- [ ] **Step 4: Implement `app/api/settings.py`**

```python
import os
import sqlite3
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Dict, Optional

router = APIRouter(prefix="/api", tags=["settings"])

def get_db_dep(db_path="data/family.db"):
    from app.database import get_connection
    conn = get_connection(db_path)
    try:
        yield conn
    finally:
        conn.close()

@router.get("/settings")
def get_settings(db: sqlite3.Connection = Depends(get_db_dep)):
    rows = db.execute("SELECT key, value FROM settings").fetchall()
    return {r["key"]: r["value"] for r in rows}

@router.put("/settings")
def update_settings(updates: Dict[str, str], db: sqlite3.Connection = Depends(get_db_dep)):
    for key, value in updates.items():
        db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (key, value))
    db.commit()
    return {"status": "updated"}

@router.get("/credentials")
def get_credentials():
    from app.config import get_config
    cfg = get_config()
    def mask(val):
        if not val: return ""
        return val[:4] + "****" + val[-2:] if len(val) > 6 else "****"
    return {
        "twilio_account_sid": mask(cfg.twilio_account_sid),
        "twilio_auth_token": mask(cfg.twilio_auth_token),
        "twilio_from_number": cfg.twilio_from_number or "",
        "twilio_whatsapp_number": cfg.twilio_whatsapp_number or "",
        "smtp_host": cfg.smtp_host or "",
        "smtp_port": cfg.smtp_port,
        "smtp_username": cfg.smtp_username or "",
        "smtp_password": mask(cfg.smtp_password),
        "smtp_from_address": cfg.smtp_from_address or "",
    }

class CredentialUpdate(BaseModel):
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_from_number: Optional[str] = None
    twilio_whatsapp_number: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from_address: Optional[str] = None

@router.put("/credentials")
def update_credentials(creds: CredentialUpdate):
    env_path = ".env"
    mapping = {
        "TWILIO_ACCOUNT_SID": creds.twilio_account_sid,
        "TWILIO_AUTH_TOKEN": creds.twilio_auth_token,
        "TWILIO_FROM_NUMBER": creds.twilio_from_number,
        "TWILIO_WHATSAPP_NUMBER": creds.twilio_whatsapp_number,
        "SMTP_HOST": creds.smtp_host,
        "SMTP_PORT": str(creds.smtp_port) if creds.smtp_port else None,
        "SMTP_USERNAME": creds.smtp_username,
        "SMTP_PASSWORD": creds.smtp_password,
        "SMTP_FROM_ADDRESS": creds.smtp_from_address,
    }
    existing = {}
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if "=" in line:
                    k, _, v = line.strip().partition("=")
                    existing[k] = v
    for k, v in mapping.items():
        if v is not None:
            existing[k] = v
    with open(env_path, "w") as f:
        for k, v in existing.items():
            f.write(f"{k}={v}\n")
    from app.config import hot_reload
    hot_reload()
    return {"status": "updated"}
```

- [ ] **Step 5: Write and run tests for logs and settings**

```python
# tests/test_api_logs.py
def test_list_logs_empty(client):
    r = client.get("/api/logs")
    assert r.status_code == 200
    assert r.json() == []

# tests/test_api_settings.py
def test_get_settings_returns_defaults(client):
    r = client.get("/api/settings")
    assert r.status_code == 200
    assert r.json()["advance_days_week"] == "7"

def test_update_settings(client):
    r = client.put("/api/settings", json={"advance_days_week": "14"})
    assert r.status_code == 200
    r2 = client.get("/api/settings")
    assert r2.json()["advance_days_week"] == "14"
```

- [ ] **Step 6: Run all API tests**

```bash
pytest tests/test_api_notifications.py tests/test_api_logs.py tests/test_api_settings.py -v
```

- [ ] **Step 7: Commit**

```bash
git add app/api/notifications.py app/api/logs.py app/api/settings.py tests/test_api_notifications.py tests/test_api_logs.py tests/test_api_settings.py
git commit -m "feat: notifications, logs, and settings API endpoints"
```

---

## Task 14: Migration Utility

**Files:**
- Create: `app/utils/migration.py`
- Create: `tests/test_migration.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_migration.py
import sqlite3, datetime
from app.database import create_tables, seed_settings
from app.utils.migration import import_json, export_json

SAMPLE = {
    "people": {
        "1": {
            "name": "John Doe",
            "phone": "7188790062",
            "birthday": "01-28",
            "birthday_notification": {"notified_week_before": True, "notified_day_before": False},
            "married": True,
            "spouse": "Venessa",
            "anniversary": "03-11",
            "anniversary_notification": {"notified_week_before": False, "notified_day_before": False}
        }
    }
}

def make_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    create_tables(conn); seed_settings(conn)
    return conn

def test_import_creates_person():
    db = make_db()
    result = import_json(SAMPLE, db)
    assert result["imported"] == 1
    row = db.execute("SELECT * FROM people WHERE name='John Doe'").fetchone()
    assert row is not None
    assert row["phone"] == "+17188790062"

def test_import_writes_state_for_true_flags():
    db = make_db()
    import_json(SAMPLE, db)
    year = datetime.date.today().year
    state = db.execute("SELECT * FROM notification_state WHERE trigger_type='7_day' AND channel='sms' AND year_sent=?", (year,)).fetchone()
    assert state is not None

def test_import_deduplicates_by_name():
    db = make_db()
    import_json(SAMPLE, db)
    import_json(SAMPLE, db)
    count = db.execute("SELECT COUNT(*) FROM people").fetchone()[0]
    assert count == 1

def test_export_roundtrip():
    db = make_db()
    import_json(SAMPLE, db)
    exported = export_json(db)
    assert len(exported["people"]) == 1
    assert exported["people"][0]["name"] == "John Doe"
```

- [ ] **Step 2: Run — expect FAIL**

```bash
pytest tests/test_migration.py -v
```

- [ ] **Step 3: Implement `app/utils/migration.py`**

```python
import datetime
import sqlite3
from app.utils.phone import normalize_phone

def import_json(data: dict, db: sqlite3.Connection) -> dict:
    people_data = data.get("people", {})
    if isinstance(people_data, list):
        people_list = people_data
    else:
        people_list = list(people_data.values())

    imported = 0
    skipped = 0
    year = datetime.date.today().year

    for p in people_list:
        name = p.get("name", "")
        existing = db.execute("SELECT id FROM people WHERE name=?", (name,)).fetchone()
        if existing:
            skipped += 1
            continue
        phone = normalize_phone(p.get("phone"))
        married = bool(p.get("married", False))
        cursor = db.execute(
            """INSERT INTO people (name, phone, birthday, married, spouse_name, anniversary)
               VALUES (?,?,?,?,?,?)""",
            (name, phone, p.get("birthday",""), married,
             p.get("spouse") or p.get("spouse_name"), p.get("anniversary"))
        )
        person_id = cursor.lastrowid
        db.commit()
        imported += 1

        bday_notif = p.get("birthday_notification", {})
        if bday_notif.get("notified_week_before"):
            _write_state(db, person_id, "birthday", "7_day", "sms", year)
        if bday_notif.get("notified_day_before"):
            _write_state(db, person_id, "birthday", "1_day", "sms", year)

        ann_notif = p.get("anniversary_notification", {})
        if ann_notif.get("notified_week_before"):
            _write_state(db, person_id, "anniversary", "7_day", "sms", year)
        if ann_notif.get("notified_day_before"):
            _write_state(db, person_id, "anniversary", "1_day", "sms", year)

    return {"imported": imported, "skipped": skipped}

def _write_state(db, person_id, event_type, trigger_type, channel, year):
    try:
        db.execute(
            "INSERT OR IGNORE INTO notification_state (person_id, event_type, trigger_type, channel, year_sent) VALUES (?,?,?,?,?)",
            (person_id, event_type, trigger_type, channel, year)
        )
        db.commit()
    except Exception:
        pass

def export_json(db: sqlite3.Connection) -> dict:
    people = [dict(r) for r in db.execute("SELECT * FROM people ORDER BY id").fetchall()]
    return {
        "exported_at": datetime.date.today().isoformat(),
        "people": people
    }
```

- [ ] **Step 4: Add import/export endpoints to `app/api/settings.py`**

```python
# Add to app/api/settings.py

@router.post("/import")
async def import_data(request: Request, db: sqlite3.Connection = Depends(get_db_dep)):
    from app.utils.migration import import_json
    body = await request.json()
    result = import_json(body, db)
    return result

@router.get("/export")
def export_data(db: sqlite3.Connection = Depends(get_db_dep)):
    from app.utils.migration import export_json
    from fastapi.responses import JSONResponse
    import datetime
    data = export_json(db)
    filename = f"family_{datetime.date.today().isoformat()}.json"
    return JSONResponse(content=data, headers={"Content-Disposition": f"attachment; filename={filename}"})
```

- [ ] **Step 5: Run — expect PASS**

```bash
pytest tests/test_migration.py -v
```

- [ ] **Step 6: Commit**

```bash
git add app/utils/migration.py app/api/settings.py tests/test_migration.py
git commit -m "feat: JSON import/export with legacy format migration"
```

---

## Task 15: FastAPI App Wiring

**Files:**
- Modify: `app/main.py`

- [ ] **Step 1: Replace `app/main.py` with full wiring**

```python
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.database import init_db
from app.config import get_config
from app.api import members, notifications, logs, settings as settings_api

def build_services():
    from app.services.twilio_sms import TwilioSMSService
    from app.services.twilio_whatsapp import TwilioWhatsAppService
    from app.services.email_smtp import EmailService
    from app.database import get_connection
    cfg = get_config()
    db = get_connection()
    sms_enabled = db.execute("SELECT value FROM settings WHERE key='sms_enabled'").fetchone()
    wa_enabled = db.execute("SELECT value FROM settings WHERE key='whatsapp_enabled'").fetchone()
    email_enabled = db.execute("SELECT value FROM settings WHERE key='email_enabled'").fetchone()
    db.close()
    services = []
    if cfg.twilio_account_sid and cfg.twilio_auth_token:
        sms = TwilioSMSService(cfg.twilio_account_sid, cfg.twilio_auth_token, cfg.twilio_from_number)
        sms.enabled = (sms_enabled and sms_enabled[0] == "true")
        services.append(sms)
        wa = TwilioWhatsAppService(cfg.twilio_account_sid, cfg.twilio_auth_token, f"whatsapp:{cfg.twilio_whatsapp_number}")
        wa.enabled = (wa_enabled and wa_enabled[0] == "true")
        services.append(wa)
    if cfg.smtp_host and cfg.smtp_username:
        email = EmailService(cfg.smtp_host, cfg.smtp_port, cfg.smtp_username, cfg.smtp_password, cfg.smtp_from_address)
        email.enabled = (email_enabled and email_enabled[0] == "true")
        services.append(email)
    return services

def create_app(db_path: str = "data/family.db") -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        init_db(db_path)
        services = build_services()
        from app.scheduler import setup_scheduler
        setup_scheduler(services, db_path)
        yield
        from app.scheduler import stop_scheduler
        stop_scheduler()

    app = FastAPI(title="Family Notification System", lifespan=lifespan)
    app.include_router(members.router)
    app.include_router(notifications.router)
    app.include_router(logs.router)
    app.include_router(settings_api.router)
    if os.path.exists("app/static"):
        app.mount("/", StaticFiles(directory="app/static", html=True), name="static")
    return app

app = create_app()
```

- [ ] **Step 2: Run the full test suite**

```bash
pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 3: Start the dev server and verify it runs**

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Expected: server starts, open `http://localhost:8000/docs` to see the API docs.

- [ ] **Step 4: Commit**

```bash
git add app/main.py
git commit -m "feat: FastAPI app wiring with lifespan, scheduler startup, and static files"
```

---

## Task 16: Dashboard Frontend

**Files:**
- Create: `app/static/index.html`
- Create: `app/static/style.css`
- Create: `app/static/app.js`

- [ ] **Step 1: Create `app/static/index.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>NoorFamily Notifications</title>
  <link rel="stylesheet" href="/style.css">
</head>
<body>
  <nav class="sidebar">
    <h1>NoorFamily</h1>
    <ul>
      <li><a href="#" data-page="members" class="active">Members</a></li>
      <li><a href="#" data-page="notifications">Notifications</a></li>
      <li><a href="#" data-page="logs">Logs</a></li>
      <li><a href="#" data-page="schedule">Schedule</a></li>
      <li><a href="#" data-page="settings">Settings</a></li>
    </ul>
  </nav>
  <main id="app"></main>
  <div id="modal-overlay" class="hidden">
    <div id="modal-box"></div>
  </div>
  <script src="/app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Create `app/static/style.css`**

```css
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body { display: flex; font-family: system-ui, sans-serif; background: #f4f6f9; color: #222; min-height: 100vh; }
.sidebar { width: 200px; background: #1a1a2e; color: #fff; padding: 24px 16px; flex-shrink: 0; }
.sidebar h1 { font-size: 1.1rem; margin-bottom: 24px; color: #a78bfa; }
.sidebar ul { list-style: none; }
.sidebar li { margin-bottom: 8px; }
.sidebar a { color: #ccc; text-decoration: none; display: block; padding: 8px 12px; border-radius: 6px; }
.sidebar a.active, .sidebar a:hover { background: #a78bfa22; color: #a78bfa; }
main { flex: 1; padding: 32px; overflow-y: auto; }
h2 { font-size: 1.4rem; margin-bottom: 20px; }
table { width: 100%; border-collapse: collapse; background: #fff; border-radius: 8px; overflow: hidden; }
th, td { padding: 12px 16px; text-align: left; border-bottom: 1px solid #eee; font-size: 0.9rem; }
th { background: #f8f9fa; font-weight: 600; }
tr:hover { background: #f8f9fa; }
.btn { padding: 8px 16px; border: none; border-radius: 6px; cursor: pointer; font-size: 0.85rem; }
.btn-primary { background: #a78bfa; color: #fff; }
.btn-danger { background: #ef4444; color: #fff; }
.btn-sm { padding: 4px 10px; font-size: 0.8rem; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; }
.badge-paused { background: #fde68a; color: #92400e; }
.badge-sent { background: #d1fae5; color: #065f46; }
.badge-failed { background: #fee2e2; color: #991b1b; }
.icon-sms, .icon-wa, .icon-email { font-size: 0.8rem; margin-right: 4px; }
.grey { color: #ccc; }
.hidden { display: none !important; }
#modal-overlay { position: fixed; inset: 0; background: #0008; display: flex; align-items: center; justify-content: center; z-index: 100; }
#modal-box { background: #fff; border-radius: 10px; padding: 32px; min-width: 420px; max-width: 600px; width: 90%; }
form label { display: block; margin-bottom: 4px; font-size: 0.85rem; font-weight: 500; }
form input, form select, form textarea { width: 100%; padding: 8px 12px; border: 1px solid #ddd; border-radius: 6px; margin-bottom: 14px; font-size: 0.9rem; }
form textarea { height: 70px; resize: vertical; }
.form-row { display: flex; gap: 12px; }
.form-row > div { flex: 1; }
.upcoming { background: #fff; border-radius: 8px; padding: 16px; margin-top: 20px; }
.upcoming h3 { font-size: 1rem; margin-bottom: 12px; }
.event-item { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #eee; font-size: 0.85rem; }
.filter-bar { display: flex; gap: 10px; margin-bottom: 16px; flex-wrap: wrap; }
.filter-bar select, .filter-bar input { padding: 6px 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 0.85rem; }
.preview-box { background: #f4f6f9; border-radius: 6px; padding: 12px; margin: 12px 0; font-size: 0.9rem; white-space: pre-wrap; }
.settings-section { background: #fff; border-radius: 8px; padding: 20px; margin-bottom: 20px; }
.settings-section h3 { margin-bottom: 14px; font-size: 1rem; }
.cred-field { position: relative; }
.cred-field input { padding-right: 60px; }
.cred-toggle { position: absolute; right: 8px; top: 8px; background: none; border: none; cursor: pointer; font-size: 0.8rem; color: #888; }
```

- [ ] **Step 3: Create `app/static/app.js`**

```javascript
// ── Router ──────────────────────────────────────────────────────────────────
const pages = {};
function registerPage(name, fn) { pages[name] = fn; }

document.querySelectorAll(".sidebar a").forEach(a => {
  a.addEventListener("click", e => {
    e.preventDefault();
    document.querySelectorAll(".sidebar a").forEach(x => x.classList.remove("active"));
    a.classList.add("active");
    navigate(a.dataset.page);
  });
});

function navigate(page) {
  document.getElementById("app").innerHTML = "";
  if (pages[page]) pages[page]();
}

// ── API helpers ──────────────────────────────────────────────────────────────
async function api(method, path, body) {
  const opts = { method, headers: { "Content-Type": "application/json" } };
  if (body) opts.body = JSON.stringify(body);
  const r = await fetch("/api" + path, opts);
  if (!r.ok) { const e = await r.text(); alert("Error: " + e); return null; }
  if (r.status === 204) return null;
  return r.json();
}

// ── Modal ────────────────────────────────────────────────────────────────────
function showModal(html) {
  document.getElementById("modal-box").innerHTML = html;
  document.getElementById("modal-overlay").classList.remove("hidden");
}
function closeModal() {
  document.getElementById("modal-overlay").classList.add("hidden");
}
document.getElementById("modal-overlay").addEventListener("click", e => {
  if (e.target === document.getElementById("modal-overlay")) closeModal();
});

// ── Channel icons ─────────────────────────────────────────────────────────────
function channelIcons(p) {
  const s = `<span class="icon-sms ${p.phone ? "" : "grey"}">SMS</span>`;
  const w = `<span class="icon-wa ${(p.whatsapp || p.phone) ? "" : "grey"}">WA</span>`;
  const e = `<span class="icon-email ${p.email ? "" : "grey"}">Email</span>`;
  return s + w + e;
}

// ── Members page ──────────────────────────────────────────────────────────────
registerPage("members", async () => {
  const [members, upcoming] = await Promise.all([
    api("GET", "/members"),
    api("GET", "/members/upcoming")
  ]);
  if (!members) return;

  const app = document.getElementById("app");
  app.innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">
      <h2>Family Members</h2>
      <button class="btn btn-primary" id="add-btn">+ Add Member</button>
    </div>
    <table>
      <thead><tr><th>Name</th><th>Birthday</th><th>Anniversary</th><th>Channels</th><th>Status</th><th>Actions</th></tr></thead>
      <tbody>
        ${members.map(m => `
          <tr>
            <td>${m.name}</td>
            <td>${m.birthday}</td>
            <td>${m.married && m.anniversary ? m.anniversary : "—"}</td>
            <td>${channelIcons(m)}</td>
            <td>${m.notifications_paused ? '<span class="badge badge-paused">Paused</span>' : ""}</td>
            <td>
              <button class="btn btn-sm btn-primary edit-btn" data-id="${m.id}">Edit</button>
              <button class="btn btn-sm btn-danger del-btn" data-id="${m.id}">Delete</button>
            </td>
          </tr>`).join("")}
      </tbody>
    </table>
    <div class="upcoming">
      <h3>Upcoming (next 30 days)</h3>
      ${upcoming.length ? upcoming.map(e => `
        <div class="event-item">
          <span>${e.name} — ${e.event_type}</span>
          <span>${e.days_away === 0 ? "TODAY" : `in ${e.days_away} days`} (${e.date})</span>
        </div>`).join("") : "<p style='color:#888;font-size:.85rem'>No upcoming events</p>"}
    </div>`;

  document.getElementById("add-btn").onclick = () => showMemberForm(null);
  document.querySelectorAll(".edit-btn").forEach(b => b.onclick = async () => {
    const m = members.find(x => x.id == b.dataset.id);
    showMemberForm(m);
  });
  document.querySelectorAll(".del-btn").forEach(b => b.onclick = async () => {
    if (confirm("Delete this member?")) {
      await api("DELETE", `/members/${b.dataset.id}`);
      navigate("members");
    }
  });
});

function showMemberForm(member) {
  const m = member || {};
  showModal(`
    <h3>${m.id ? "Edit" : "Add"} Member</h3>
    <form id="member-form" style="margin-top:16px">
      <div class="form-row">
        <div><label>Name *</label><input name="name" value="${m.name || ""}" required></div>
        <div><label>Birthday (MM-DD) *</label><input name="birthday" value="${m.birthday || ""}" placeholder="01-28" required></div>
      </div>
      <div class="form-row">
        <div><label>Phone (US 10-digit)</label><input name="phone" value="${m.phone || ""}"></div>
        <div><label>Email</label><input name="email" type="email" value="${m.email || ""}"></div>
      </div>
      <div class="form-row">
        <div><label>WhatsApp (if different)</label><input name="whatsapp" value="${m.whatsapp || ""}"></div>
        <div><label>Birth Year (for age)</label><input name="birth_year" type="number" value="${m.birth_year || ""}"></div>
      </div>
      <div style="margin-bottom:14px">
        <label><input type="checkbox" name="married" ${m.married ? "checked" : ""}> Married</label>
      </div>
      <div id="married-fields" style="${m.married ? "" : "display:none"}">
        <div class="form-row">
          <div><label>Spouse Name</label><input name="spouse_name" value="${m.spouse_name || ""}"></div>
          <div><label>Anniversary (MM-DD)</label><input name="anniversary" value="${m.anniversary || ""}"></div>
        </div>
        <div><label>Anniversary Year</label><input name="anniversary_year" type="number" value="${m.anniversary_year || ""}"></div>
      </div>
      <label>Custom Birthday Message</label>
      <textarea name="custom_birthday_message">${m.custom_birthday_message || ""}</textarea>
      <label>Custom Anniversary Message</label>
      <textarea name="custom_anniversary_message">${m.custom_anniversary_message || ""}</textarea>
      <label><input type="checkbox" name="notifications_paused" ${m.notifications_paused ? "checked" : ""}> Pause Notifications</label>
      <div style="display:flex;gap:10px;margin-top:20px">
        <button type="submit" class="btn btn-primary">${m.id ? "Update" : "Add"}</button>
        <button type="button" class="btn" onclick="closeModal()">Cancel</button>
      </div>
    </form>`);

  document.querySelector('[name="married"]').onchange = e => {
    document.getElementById("married-fields").style.display = e.target.checked ? "" : "none";
  };
  document.getElementById("member-form").onsubmit = async e => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const data = Object.fromEntries(fd);
    data.married = !!fd.get("married");
    data.notifications_paused = !!fd.get("notifications_paused");
    if (data.birth_year) data.birth_year = parseInt(data.birth_year);
    if (data.anniversary_year) data.anniversary_year = parseInt(data.anniversary_year);
    const url = m.id ? `/members/${m.id}` : "/members";
    const method = m.id ? "PUT" : "POST";
    const result = await api(method, url, data);
    if (result) { closeModal(); navigate("members"); }
  };
}

// ── Notifications page ────────────────────────────────────────────────────────
registerPage("notifications", async () => {
  const members = await api("GET", "/members");
  if (!members) return;
  document.getElementById("app").innerHTML = `
    <h2>Send Notifications</h2>
    <div class="settings-section">
      <div class="form-row">
        <div><label>Person</label>
          <select id="notif-person">
            ${members.map(m => `<option value="${m.id}">${m.name}</option>`).join("")}
          </select>
        </div>
        <div><label>Event Type</label>
          <select id="notif-event"><option value="birthday">Birthday</option><option value="anniversary">Anniversary</option></select>
        </div>
        <div><label>Trigger</label>
          <select id="notif-trigger">
            <option value="same_day">Same Day (wish)</option>
            <option value="1_day">1-Day Advance (reminder)</option>
            <option value="7_day">7-Day Advance (reminder)</option>
          </select>
        </div>
      </div>
      <div style="display:flex;gap:10px">
        <button class="btn btn-primary" id="preview-btn">Preview</button>
        <button class="btn" style="background:#10b981;color:#fff" id="send-btn">Send Now</button>
      </div>
      <div id="preview-result" style="margin-top:16px"></div>
    </div>`;

  const getPayload = () => ({
    person_id: parseInt(document.getElementById("notif-person").value),
    event_type: document.getElementById("notif-event").value,
    trigger_type: document.getElementById("notif-trigger").value,
  });

  document.getElementById("preview-btn").onclick = async () => {
    const result = await api("POST", "/notifications/preview", getPayload());
    if (result) {
      document.getElementById("preview-result").innerHTML = `
        <strong>SMS / WhatsApp:</strong><div class="preview-box">${result.sms}</div>
        <strong>Email:</strong><div class="preview-box">${result.email}</div>`;
    }
  };
  document.getElementById("send-btn").onclick = async () => {
    if (confirm("Send this notification now?")) {
      const result = await api("POST", "/notifications/send", getPayload());
      if (result) alert("Notification dispatched!");
    }
  };
});

// ── Logs page ─────────────────────────────────────────────────────────────────
registerPage("logs", async () => {
  document.getElementById("app").innerHTML = `
    <h2>Notification Logs</h2>
    <div class="filter-bar">
      <select id="f-channel"><option value="">All channels</option><option>sms</option><option>whatsapp</option><option>email</option></select>
      <select id="f-status"><option value="">All statuses</option><option value="sent">Sent</option><option value="failed">Failed</option></select>
      <select id="f-event"><option value="">All events</option><option value="birthday">Birthday</option><option value="anniversary">Anniversary</option></select>
      <button class="btn btn-primary btn-sm" id="f-apply">Filter</button>
    </div>
    <div id="logs-table"></div>`;

  async function loadLogs() {
    const params = new URLSearchParams();
    const channel = document.getElementById("f-channel").value;
    const status = document.getElementById("f-status").value;
    const event = document.getElementById("f-event").value;
    if (channel) params.set("channel", channel);
    if (status) params.set("status", status);
    if (event) params.set("event_type", event);
    const logs = await api("GET", `/logs?${params}`);
    if (!logs) return;
    document.getElementById("logs-table").innerHTML = logs.length ? `
      <table>
        <thead><tr><th>Person</th><th>Event</th><th>Trigger</th><th>Channel</th><th>Status</th><th>Sent At</th><th>Action</th></tr></thead>
        <tbody>${logs.map(l => `
          <tr>
            <td>${l.person_name}</td>
            <td>${l.event_type}</td>
            <td>${l.trigger_type}</td>
            <td>${l.channel}</td>
            <td><span class="badge badge-${l.status}">${l.status}${l.error_message ? ` — ${l.error_message}` : ""}</span></td>
            <td>${l.sent_at}</td>
            <td>${l.status === "failed" ? `<button class="btn btn-sm btn-primary retry-btn" data-id="${l.id}">Retry</button>` : ""}</td>
          </tr>`).join("")}
        </tbody>
      </table>` : "<p style='color:#888'>No logs found.</p>";
    document.querySelectorAll(".retry-btn").forEach(b => b.onclick = async () => {
      await api("POST", `/logs/${b.dataset.id}/retry`);
      loadLogs();
    });
  }
  document.getElementById("f-apply").onclick = loadLogs;
  loadLogs();
});

// ── Schedule page ─────────────────────────────────────────────────────────────
registerPage("schedule", async () => {
  const settings = await api("GET", "/settings");
  if (!settings) return;
  document.getElementById("app").innerHTML = `
    <h2>Schedule</h2>
    <div class="settings-section">
      <h3>Advance Reminder Windows</h3>
      <div class="form-row">
        <div><label>Week-ahead reminder (days before)</label><input id="s-week" type="number" value="${settings.advance_days_week}"></div>
        <div><label>Day-before reminder (days before)</label><input id="s-day" type="number" value="${settings.advance_days_day}"></div>
      </div>
      <h3 style="margin-top:16px">Job Times</h3>
      <div class="form-row">
        <div><label>Advance reminders run at</label><input id="s-job1" type="time" value="${settings.job1_time}"></div>
        <div><label>Day-of wishes run at</label><input id="s-job2" type="time" value="${settings.job2_time}"></div>
      </div>
      <div><label>Catch-up window (hours)</label><input id="s-catchup" type="number" value="${settings.catch_up_hours}" style="max-width:120px"></div>
      <h3 style="margin-top:16px">Channels</h3>
      <label><input type="checkbox" id="s-sms" ${settings.sms_enabled === "true" ? "checked" : ""}> Enable SMS</label><br>
      <label><input type="checkbox" id="s-wa" ${settings.whatsapp_enabled === "true" ? "checked" : ""}> Enable WhatsApp</label><br>
      <label><input type="checkbox" id="s-email" ${settings.email_enabled === "true" ? "checked" : ""}> Enable Email</label>
      <div style="margin-top:20px">
        <button class="btn btn-primary" id="save-schedule">Save</button>
      </div>
    </div>`;

  document.getElementById("save-schedule").onclick = async () => {
    await api("PUT", "/settings", {
      advance_days_week: document.getElementById("s-week").value,
      advance_days_day: document.getElementById("s-day").value,
      job1_time: document.getElementById("s-job1").value,
      job2_time: document.getElementById("s-job2").value,
      catch_up_hours: document.getElementById("s-catchup").value,
      sms_enabled: document.getElementById("s-sms").checked ? "true" : "false",
      whatsapp_enabled: document.getElementById("s-wa").checked ? "true" : "false",
      email_enabled: document.getElementById("s-email").checked ? "true" : "false",
    });
    alert("Schedule saved!");
  };
});

// ── Settings page ─────────────────────────────────────────────────────────────
registerPage("settings", async () => {
  const creds = await api("GET", "/credentials");
  if (!creds) return;
  document.getElementById("app").innerHTML = `
    <h2>Settings</h2>
    <div class="settings-section">
      <h3>Twilio (SMS + WhatsApp)</h3>
      ${credField("twilio_account_sid", "Account SID", creds.twilio_account_sid)}
      ${credField("twilio_auth_token", "Auth Token", creds.twilio_auth_token)}
      ${credField("twilio_from_number", "From Number", creds.twilio_from_number, false)}
      ${credField("twilio_whatsapp_number", "WhatsApp Number", creds.twilio_whatsapp_number, false)}
    </div>
    <div class="settings-section">
      <h3>Email (SMTP)</h3>
      ${credField("smtp_host", "SMTP Host", creds.smtp_host, false)}
      <div class="form-row">
        <div>${credField("smtp_port", "Port", String(creds.smtp_port), false)}</div>
        <div>${credField("smtp_username", "Username", creds.smtp_username, false)}</div>
      </div>
      ${credField("smtp_password", "Password", creds.smtp_password)}
      ${credField("smtp_from_address", "From Address", creds.smtp_from_address, false)}
    </div>
    <button class="btn btn-primary" id="save-creds">Save Credentials</button>
    <div class="settings-section" style="margin-top:20px">
      <h3>Data</h3>
      <div style="display:flex;gap:10px;flex-wrap:wrap">
        <button class="btn btn-primary" id="export-btn">Export JSON</button>
        <label class="btn" style="background:#6b7280;color:#fff;cursor:pointer">
          Import JSON <input type="file" accept=".json" id="import-file" style="display:none">
        </label>
      </div>
    </div>`;

  document.querySelectorAll(".cred-toggle").forEach(btn => {
    btn.onclick = () => {
      const inp = btn.previousElementSibling;
      inp.type = inp.type === "password" ? "text" : "password";
      btn.textContent = inp.type === "password" ? "Show" : "Hide";
    };
  });

  document.getElementById("save-creds").onclick = async () => {
    const data = {};
    document.querySelectorAll(".cred-input").forEach(inp => { data[inp.name] = inp.value; });
    data.smtp_port = parseInt(data.smtp_port) || 587;
    await api("PUT", "/credentials", data);
    alert("Credentials saved and reloaded!");
  };

  document.getElementById("export-btn").onclick = () => {
    window.location.href = "/api/export";
  };

  document.getElementById("import-file").onchange = async e => {
    const file = e.target.files[0];
    if (!file) return;
    const text = await file.text();
    const json = JSON.parse(text);
    const result = await api("POST", "/import", json);
    if (result) alert(`Imported: ${result.imported}, Skipped: ${result.skipped}`);
  };
});

function credField(name, label, value, masked = true) {
  return `
    <label>${label}</label>
    <div class="cred-field">
      <input class="cred-input" name="${name}" type="${masked ? "password" : "text"}" value="${value || ""}">
      ${masked ? '<button type="button" class="cred-toggle">Show</button>' : ""}
    </div>`;
}

// ── Init ──────────────────────────────────────────────────────────────────────
navigate("members");
```

- [ ] **Step 4: Start the server and test all 5 pages manually**

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000` and verify:
- Members: add a test member, edit, delete, view upcoming panel
- Notifications: select member, preview message, send now
- Logs: verify sends appear, failed entries show retry button
- Schedule: change advance days, save, verify persisted via GET /api/settings
- Settings: masked credential fields, export downloads JSON

- [ ] **Step 5: Commit**

```bash
git add app/static/
git commit -m "feat: dashboard frontend — all 5 pages with full controls"
```

---

## Task 17: systemd Unit + Pi Deployment

**Files:**
- Create: `systemd/family-notifier.service`

- [ ] **Step 1: Create `systemd/family-notifier.service`**

```ini
[Unit]
Description=Family Notification System
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/family-notification-system
ExecStart=/home/pi/family-notification-system/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=on-failure
RestartSec=5
EnvironmentFile=/home/pi/family-notification-system/.env

[Install]
WantedBy=multi-user.target
```

- [ ] **Step 2: Pi deployment steps**

Run these commands on the Pi via SSH:

```bash
# Clone or copy project to Pi
scp -r . pi@raspberrypi.local:/home/pi/family-notification-system

# SSH into Pi
ssh pi@raspberrypi.local

# Set up Python venv
cd /home/pi/family-notification-system
python3 -m venv venv
venv/bin/pip install -r requirements.txt

# Copy .env.example and fill in real credentials
cp .env.example .env
nano .env

# Create data directory
mkdir -p data/exports

# Install systemd service
sudo cp systemd/family-notifier.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable family-notifier
sudo systemctl start family-notifier

# Verify it's running
sudo systemctl status family-notifier
```

Expected: service shows `active (running)`.

- [ ] **Step 3: Verify from browser**

Open `http://raspberrypi.local:8000` on any device on your home network.

- [ ] **Step 4: Import existing family data**

On the Settings page, click **Import JSON**, select your `dates_family.json` file.

Expected: members appear in the Members page.

- [ ] **Step 5: Commit**

```bash
git add systemd/family-notifier.service
git commit -m "feat: systemd unit for Pi 5 deployment"
```

---

## Task 18: Run Full Test Suite + Final Verification

- [ ] **Step 1: Run all tests**

```bash
pytest tests/ -v --tb=short
```

Expected: all tests pass.

- [ ] **Step 2: Verify API docs**

Open `http://localhost:8000/docs` — confirm all endpoints are listed and documented.

- [ ] **Step 3: End-to-end smoke test**

```bash
# Add a member with today's birthday
curl -X POST http://localhost:8000/api/members \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Person","birthday":"'$(date +%m-%d)'","phone":"7188790062"}'

# Preview the day-of wish
curl -X POST http://localhost:8000/api/notifications/preview \
  -H "Content-Type: application/json" \
  -d '{"person_id":1,"event_type":"birthday","trigger_type":"same_day"}'

# Verify upcoming events
curl http://localhost:8000/api/members/upcoming
```

- [ ] **Step 4: Tag the release**

```bash
git tag v1.0.0
git log --oneline
```

---

## Dependency Order

```
Task 1 (scaffold) → Task 2 (config) → Task 3 (database) → Task 4 (phone) → Task 5 (messaging)
→ Task 6 (base service) → Tasks 7,8,9 (plugins, parallel) → Task 10 (sender)
→ Task 11 (scheduler) → Tasks 12,13 (APIs, parallel) → Task 14 (migration)
→ Task 15 (main.py wiring) → Task 16 (frontend) → Task 17 (deployment) → Task 18 (verification)
```
