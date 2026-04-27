# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Setup (Python 3.11+)
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # then fill in real Twilio + SMTP credentials

# Run the app (serves API + dashboard at http://localhost:8000)
uvicorn app.main:app --reload                    # dev
uvicorn app.main:app --host 0.0.0.0 --port 8000  # prod / Pi

# Tests
pytest                                # full suite
pytest tests/test_scheduler.py        # one file
pytest tests/test_scheduler.py::test_advance_reminders_fires_7_day  # one test
pytest -k "advance" -v                # by keyword
```

`pytest.ini` sets `asyncio_mode = auto` — async tests don't need decorators.

## Architecture

**Single FastAPI process** that serves the REST API, the static dashboard (`app/static/`), and runs the APScheduler in-process via the FastAPI lifespan. SQLite (`data/family.db`) is the single source of truth. Deployed on a Raspberry Pi via the systemd unit template in `systemd/family-notifier.service` (placeholders `__USER__` / `__APP_DIR__` / `__PORT__` are substituted by `install.sh`). Default prod port is **8001**; dev examples below use 8000 just so they don't clash with a running prod instance on the same host.

### Wiring (read this before changing startup behavior)

`app/main.py:create_app()` is the composition root. On lifespan startup it:
1. Calls `init_db()` to create tables and seed `settings` defaults.
2. Calls `_build_services()` which reads `.env` via `app.config.get_config()` AND the `settings` table to construct only the services whose credentials are present *and* whose `<channel>_enabled` flag is true. The result is a list of `NotificationService` instances.
3. Passes that list to `app/scheduler.py:setup_scheduler()`, which stores it in module-level state (`_services`, `_db_path`) and registers two cron jobs.

The API layer reaches the live service list via `app.scheduler.get_services()` — do not import the services module-globals from elsewhere. The DB path is injected through `app.api.deps.set_db_path()` and read by the `get_db` FastAPI dependency.

### The two scheduled jobs (`app/scheduler.py`)

- **`run_advance_reminders`** (default 08:00) — for each unpaused person, fires when their birthday/anniversary is exactly `advance_days_week` (default 7) or `advance_days_day` (default 1) days away. Recipients: **all OTHER family members** (group reminder), each on their own enabled channels. `trigger_type` written to state: `7_day` / `1_day`.
- **`run_day_of_wishes`** (default 12:00) — fires when the event is today. Recipient: **the person themselves**. `trigger_type`: `same_day`. Has `misfire_grace_time = catch_up_hours * 3600` so a Pi that boots late still sends.

Settings keys that drive scheduling: `job1_time`, `job2_time`, `advance_days_week`, `advance_days_day`, `catch_up_hours`. Changing them via the API requires a restart to take effect (jobs are registered once at startup).

### Idempotency model — non-obvious

Two separate tables for two purposes:
- `notification_state` — duplicate-prevention. UNIQUE on `(person_id, event_type, trigger_type, channel, year_sent)`. **Written only on successful send.** A failure on one channel does NOT block retry on that channel; success on SMS does NOT block a separate fire on email.
- `notification_log` — full audit trail of every attempt (sent or failed).

`app/utils/sender.py:execute_send()` is the single chokepoint that enforces this. It loops services, checks `already_sent()` per channel when `write_state=True`, sends, logs, and only writes state on success.

The `write_state` flag is the subtle part — these rules are enforced by callers, not by `execute_send` itself:
- Scheduler jobs → `write_state=True` (always idempotent).
- `POST /api/notifications/send` (manual) → `write_state=True` only when `trigger_type == "same_day"`. Manual `7_day`/`1_day` sends do NOT write state, so the scheduled advance reminder still fires on its normal day. Manual same-day DOES write state to prevent the noon catch-up from re-firing.
- `POST /api/logs/{id}/retry` → `write_state=False` and is filtered to a single channel (`services = [s for s in get_services() if s.name == log["channel"]]`) so other channels are untouched.

### Notification plugin pattern (`app/services/`)

`NotificationService` (in `base.py`) is the contract: `name`, `enabled`, `send(person, message) -> bool`, `health_check() -> bool`. Each plugin extracts its own contact field from `person`:
- `TwilioSMSService` → `person["phone"]`
- `TwilioWhatsAppService` → `person["whatsapp"] or person["phone"]` (the WhatsApp field stores NULL when it equals the phone — see members.py / migration.py)
- `EmailService` → `person["email"]`

A plugin returns `True` when the contact field is empty (a skip is not a failure). Adding a new channel means: one new file in `services/`, register it in `app/main.py:_build_services()`, add a `<channel>_enabled` row to `database.DEFAULTS`, and ensure the per-plugin contact field exists on the `people` table.

### Credentials & hot-reload

Credentials live ONLY in `.env`, never in SQLite. `app/config.py` is a module-level singleton (`_config`) loaded by `load_dotenv(override=True)`. `PUT /api/credentials` rewrites `.env` in place and calls `hot_reload()` — but in-memory service instances built at startup are NOT recreated, so credential changes don't reach already-running services until restart. `GET /api/credentials` masks secrets before returning.

### Message rendering (`app/utils/messaging.py`)

Default templates live in the `DEFAULTS` dict keyed by `(event_type, "advance"|"same_day", for_person: bool)`. `for_person=True` is used only for `same_day`. `render_message()` substitutes `{name}`, `{spouse}`, `{day_of_week}`, `{days}`, `{age}`, `{years_married}`. If `birth_year`/`anniversary_year` is missing, the corresponding `{age}`/`{years_married}` placeholder is *stripped along with one leading space* via regex — be careful when editing this; it is the reason templates can mention `{age}` unconditionally.

### Phone normalization (`app/utils/phone.py`)

All phones stored as E.164 (`+1XXXXXXXXXX`). 10-digit input gets `+1` prepended; 11-digit starting with `1` gets `+`; explicit `+` input is validated for length 7–15. Both `members.py` create/update and `migration.py` import call `normalize_phone()`. The "WhatsApp same as phone → store NULL" rule is enforced at the API layer, not in the DB.

## Tests

`tests/conftest.py` provides:
- `db` fixture — in-memory SQLite with one seeded person (`John`, birthday `01-28`).
- `client` fixture — `TestClient(create_app(db_path=tmp_path/test.db, start_scheduler=False))`. **Always pass `start_scheduler=False` in tests** so APScheduler isn't started.
- `mock_sms_service` — captures sends in `svc.calls`.

When testing scheduler logic, build services manually and call `setup_scheduler([...], db_path)` or invoke `run_advance_reminders` / `run_day_of_wishes` directly after monkeypatching `_services` / `_db_path`.

## Branding

`FAMILY_NAME` in `.env` (read via `app.config.get_config().family_name`, default `"Family"`) is exposed at `GET /api/branding` and applied at runtime by `app/static/app.js` — it sets the document title, sidebar/topbar brand text, and logo `alt`. The email subject fallback in `app.services.email_smtp._build_subject` also uses it. Treat it as a deploy-time setting (changes require a process restart for the SMTP path; the dashboard re-fetches branding on every page load).
