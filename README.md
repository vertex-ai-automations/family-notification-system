# NoorFamily Notification System

Self-hosted birthday and anniversary notifications for your family — runs on a Raspberry Pi, sends via SMS, WhatsApp, and email, managed through a local web dashboard. Designed to replace a pair of one-off Twilio scripts with a single always-on service.

---

## What it does

- Sends **advance reminders** (default: 7 days and 1 day before) to *every other family member* — "Don't forget Anum's birthday is in 7 days!"
- Sends **same-day wishes** directly to the person whose event it is — "Happy Birthday, Anum!"
- Three channels — SMS, WhatsApp, Email — picked per-recipient based on which contact fields are populated.
- Idempotent: each (person, event, trigger, channel) sends at most once per calendar year. Retries respect that boundary.
- Catches up missed runs after a reboot — if the Pi was offline at noon, it still fires once if it's back within `catch_up_hours`.
- Dashboard at `http://<host>:<port>` for managing members, previewing messages, viewing logs, and editing schedule/credentials live.

---

## Architecture (one-minute version)

```
┌──────────────────────────────────────────────────┐
│  FastAPI process (single, managed by systemd)    │
│                                                  │
│  ┌──────────────┐    ┌────────────────────────┐  │
│  │ APScheduler  │    │ REST API + dashboard   │  │
│  │ (in-process) │    │  /api/members          │  │
│  │  Job 1: 8am  │    │  /api/notifications    │  │
│  │  Job 2: noon │    │  /api/logs             │  │
│  └──────┬───────┘    │  /api/settings         │  │
│         │            │  /api/credentials      │  │
│         │            │  /api/import|export    │  │
│         │            │  /health               │  │
│         │            └────────┬───────────────┘  │
│         ▼                     ▼                  │
│  ┌──────────────────────────────────────┐        │
│  │ NotificationService plugins (3)      │        │
│  │  TwilioSMS · TwilioWhatsApp · Email  │        │
│  └──────────────────────────────────────┘        │
│                  │                                │
│                  ▼                                │
│           SQLite (data/family.db)                 │
│            people / settings                      │
│            notification_state (idempotency)       │
│            notification_log    (audit trail)      │
└──────────────────────────────────────────────────┘
```

Every notification flows through a single chokepoint (`app/utils/sender.py:execute_send`) which enforces the idempotency rules. Adding a fourth channel (e.g. Pushover, ntfy) is one new file in `app/services/`.

See `CLAUDE.md` for the developer-facing architecture detail.

---

## Quick start

```bash
git clone <this repo> family-notification-system
cd family-notification-system

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env with real Twilio + SMTP credentials

# Run it
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

Open `http://localhost:8001`. Five tabs in the sidebar:
- **Members** — add/edit/remove people, see upcoming events
- **Notifications** — preview & send manually, pause/resume per person
- **Logs** — full history with filters and one-click retry
- **Schedule** — change job times, advance-reminder windows, channel toggles
- **Settings** — Twilio + SMTP credentials, JSON import/export

Requires Python 3.11+.

---

## Configuration

### `.env` — credentials only

```
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_FROM_NUMBER=+18772539457
TWILIO_WHATSAPP_NUMBER=+14155238886
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your@gmail.com
SMTP_PASSWORD=your-app-password   # for Gmail use an App Password, not your real one
SMTP_FROM_ADDRESS=your@gmail.com
TZ=America/Chicago                # optional; defaults to America/Chicago
```

`PUT /api/credentials` (Settings page) rewrites `.env` atomically (preserves comments and unrelated keys), reloads config, and rebuilds running service instances — **no restart required.**

### `settings` table — schedule and channel toggles

| Key | Default | Description |
|---|---|---|
| `advance_days_week` | `7` | Days before for the "week-ahead" reminder window |
| `advance_days_day` | `1` | Days before for the "day-before" reminder window |
| `job1_time` | `08:00` | When advance reminders fire |
| `job2_time` | `12:00` | When same-day wishes fire |
| `catch_up_hours` | `6` | Window after `job2_time` for a startup catch-up to still fire |
| `sms_enabled` | `true` | Global SMS toggle |
| `whatsapp_enabled` | `true` | Global WhatsApp toggle |
| `email_enabled` | `true` | Global Email toggle |

Schedule and channel-toggle changes apply **live** through `PUT /api/settings` — no restart.

---

## Data model

### `people`
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `name` | TEXT | Used for dedup on import |
| `phone` | TEXT | E.164, e.g. `+17188790062`. UI auto-prepends `+1` for 10-digit US |
| `email` | TEXT | Optional |
| `whatsapp` | TEXT | E.164. Stored `NULL` when same as phone — WhatsApp send is skipped (not fallback) when not set |
| `birthday` | TEXT | `MM-DD` |
| `birth_year` | INTEGER | Optional, enables `{age}` template var |
| `married` | BOOLEAN | When 0, anniversary fields are ignored even if populated |
| `spouse_name`, `anniversary`, `anniversary_year` | | Anniversary side; `anniversary` is `MM-DD` |
| `custom_birthday_message`, `custom_anniversary_message` | TEXT | Templated; falls back to defaults when empty |
| `notifications_paused` | BOOLEAN | Pauses *both* advance reminders to others *and* same-day wishes |

### `notification_state` — idempotency
UNIQUE on `(person_id, event_type, trigger_type, channel, year_sent)`. Written **only on successful send**. A failure on one channel does not block retry on that channel; success on SMS does not block email.

### `notification_log` — full audit trail
Every send attempt — sent or failed — with rendered `message_body`, `status`, and (for failures) the captured exception in `error_message`.

### Message template variables

Available in `custom_birthday_message`, `custom_anniversary_message`, and the built-in defaults:

| Variable | Resolves to |
|---|---|
| `{name}` | Person's name |
| `{spouse}` | Spouse name |
| `{age}` | `today.year - birth_year` (placeholder + leading space stripped if `birth_year` is null) |
| `{years_married}` | Same logic for `anniversary_year` |
| `{day_of_week}` | e.g. `"Monday"` |
| `{days}` | Integer days to event — `7`, `1`, or `0` |

Built-in defaults live in `app/utils/messaging.py:DEFAULTS`.

---

## API reference

| Method | Path | Body / params | Notes |
|---|---|---|---|
| `GET`  | `/health` | — | DB + per-service health checks |
| `GET`  | `/api/members` | — | All members |
| `GET`  | `/api/members/upcoming` | — | Events in next 30 days |
| `POST` | `/api/members` | `PersonCreate` | E.164 normalization auto-applied |
| `PUT`  | `/api/members/{id}` | `PersonUpdate` (full) | Replace all fields |
| `PATCH`| `/api/members/{id}` | `PersonPartialUpdate` | Single-field updates |
| `DELETE` | `/api/members/{id}` | — | Cascades to logs and state |
| `PUT`  | `/api/members/{id}/pause` | `{"paused": bool}` | Toggle |
| `POST` | `/api/notifications/preview` | `{person_id, event_type, trigger_type}` | Returns rendered message per channel |
| `POST` | `/api/notifications/send` | same | Manual fire — bypasses state for `7_day`/`1_day`, writes state for `same_day` |
| `GET`  | `/api/logs` | filters: `person_id`, `channel`, `event_type`, `trigger_type`, `status`, `date_from`, `date_to` | Last 500 rows |
| `POST` | `/api/logs/{log_id}/retry` | — | Re-fires only the failed channel of that row |
| `GET`  | `/api/settings` | — | All settings |
| `PUT`  | `/api/settings` | `{key: value, ...}` | Validated; live-applies |
| `GET`  | `/api/credentials` | — | Returns masked values |
| `PUT`  | `/api/credentials` | `CredentialUpdate` | Atomically updates `.env` + reloads |
| `GET`  | `/api/export` | — | JSON export of all members |
| `POST` | `/api/import` | export-format JSON, or legacy dict-of-dicts | Dedups by name |

Pydantic models live in `app/models.py`.

---

## JSON import / export

The importer accepts two shapes — both must have a top-level `people` key.

**New format (what `/api/export` produces) — list:**

```json
{
  "exported_at": "2026-04-26",
  "people": [
    {
      "name": "John Doe",
      "phone": "+17188790062",
      "email": "john@example.com",
      "whatsapp": null,
      "birthday": "01-28",
      "birth_year": 1980,
      "married": true,
      "spouse_name": "Venessa",
      "anniversary": "03-11",
      "anniversary_year": 2005,
      "custom_birthday_message": "",
      "custom_anniversary_message": "",
      "notifications_paused": false
    }
  ]
}
```

**Legacy format — dict-of-dicts (original `dates_*.json` shape from the predecessor scripts):**

```json
{
  "people": {
    "1": {
      "name": "John Doe",
      "phone": "7188790062",
      "birthday": "01-28",
      "married": true,
      "spouse": "Venessa",
      "anniversary": "03-11",
      "birthday_notification": { "notified_week_before": false, "notified_day_before": false }
    }
  }
}
```

For legacy imports, `notified_week_before` / `notified_day_before` flags translate into `notification_state` rows for the **`sms` channel only** (matching the old scripts' behavior) so SMS doesn't re-fire but WhatsApp/email still send fresh.

Imports dedup by `name`.

---

## Running on a Raspberry Pi (systemd)

```bash
# Edit the unit file to match your username + path
$EDITOR systemd/family-notifier.service

sudo cp systemd/family-notifier.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now family-notifier.service
sudo systemctl status family-notifier.service
journalctl -u family-notifier.service -f
```

Default port is `8001` to avoid collision with other services. The unit auto-starts on boot and restarts on crash. RAM footprint: ~50–80 MB.

Reachable from any device on your home network at `http://<pi-hostname>.local:8001`.

---

## Testing

```bash
pytest                                                  # full suite (77 tests)
pytest tests/test_scheduler.py                          # one file
pytest tests/test_scheduler.py::test_day_of_wishes_sends_to_birthday_person
pytest -k advance -v                                    # by keyword
```

`pytest.ini` enables `asyncio_mode = auto`. Unit tests use `:memory:` SQLite; API tests get a fresh DB per `client` fixture and pass `start_scheduler=False` so APScheduler doesn't start during tests.

---

## Project layout

```
family-notification-system/
├── app/
│   ├── main.py                  # FastAPI app + lifespan
│   ├── service_factory.py       # Builds services from .env + settings table
│   ├── scheduler.py             # APScheduler jobs + reschedule + catch-up
│   ├── database.py              # SQLite schema, defaults, WAL
│   ├── models.py                # Pydantic models
│   ├── config.py                # .env loading + hot reload
│   ├── api/
│   │   ├── members.py           # CRUD + PATCH + upcoming
│   │   ├── notifications.py     # Preview / Send Now / Pause
│   │   ├── logs.py              # List + retry
│   │   ├── settings.py          # Settings + credentials + import/export
│   │   └── health.py            # /health
│   ├── services/
│   │   ├── base.py              # NotificationService ABC
│   │   ├── twilio_sms.py
│   │   ├── twilio_whatsapp.py
│   │   └── email_smtp.py
│   ├── utils/
│   │   ├── sender.py            # execute_send — single chokepoint
│   │   ├── messaging.py         # Templates + render
│   │   ├── phone.py             # E.164 normalization
│   │   ├── retry.py             # Exponential backoff helper
│   │   └── migration.py         # JSON import / export
│   └── static/                  # Dashboard SPA (HTML/CSS/JS)
├── data/
│   ├── family.db                # SQLite DB (gitignored)
│   └── exports/                 # JSON exports (gitignored)
├── tests/                       # pytest suite
├── systemd/family-notifier.service
├── docs/superpowers/            # Original design spec + plan
├── requirements.txt
└── pytest.ini
```

---

## Troubleshooting

**Service stuck in restart loop.** Probably another process owns the port. `journalctl -u family-notifier.service -n 30` will show `address already in use`. Either stop the other service or change `--port` in the systemd unit.

**Dashboard shows "Bot is running" or some unrelated page.** A different app on the same port answered first. See above.

**Failed sends with no error in the log.** Pre-`error_message` fix — pull latest. Now every failure logs the captured exception string.

**WhatsApp not sending despite person having a phone.** Behavior change: WhatsApp only sends when the person has an *explicit* WhatsApp number. Sending to plain phone numbers via the Twilio sandbox almost always fails and floods the log. Set `whatsapp` explicitly per person.

**Schedule changes don't seem to apply.** They should now — the API live-reschedules. If you're on an older build that didn't, restart the service.

**Same-day Send Now is silently skipped on retry.** Same-day manual sends write a `notification_state` row to prevent the noon catch-up from double-sending. If you need to test repeatedly, either use `7_day` / `1_day` triggers (which don't write state on manual send) or delete the state rows for that person.

---

## Security notes

- Credentials live exclusively in `.env`. Never in SQLite, never returned unmasked from the API.
- No authentication on the dashboard — assumes a trusted home network. **Do not expose port directly to the internet.** If you need remote access, put it behind Tailscale or a VPN.
- The atomic `.env` writer preserves comments and avoids partial-write corruption.
