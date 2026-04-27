# Family Notification System

Self-hosted birthday and anniversary notifications for your family — runs on a Raspberry Pi (or any small Linux box / VPS), sends via SMS, WhatsApp, and email, managed through a local web dashboard. Single-process, single SQLite file, ~50–80 MB RAM.

> **Heads up:** this app is designed for a *trusted home network*. The dashboard has no auth — do not expose it directly to the public internet. Use Tailscale / WireGuard / a VPN if you need remote access.

---

## Features

- **Advance reminders** (default: 7 days and 1 day before) sent to *every other* family member — *"Don't forget Anum's birthday is in 7 days!"*
- **Same-day wishes** sent to the person whose event it is — *"Happy Birthday, Anum!"*
- **Three notification channels** — SMS, WhatsApp, Email — chosen per recipient based on which contact fields are populated. Each channel can be globally toggled on/off live, no restart.
- **Idempotent by construction** — each `(person, event, trigger, channel)` sends at most once per calendar year. A failure on one channel does *not* block retry on that channel; success on SMS does *not* block email.
- **Catch-up after reboot** — if the Pi was offline at noon, it still fires once when it comes back, within the configurable `catch_up_hours` window.
- **Family tree visualization** — interactive D3-powered family tree (powered by [`family-chart`](https://github.com/donatso/family-chart), MIT) drawn from `mother_id` / `father_id` / `spouse_id` relationship columns. Multiple disjoint clusters supported via a focus picker.
- **Per-person customization** — pause notifications, override default message templates per person, mark anyone as unmarried to skip anniversary handling.
- **Manual send + retry** — preview rendered messages per channel, send one-off, or retry a failed log entry against a single channel.
- **JSON import / export** — back up your roster, migrate from the legacy `dates_*.json` predecessor scripts, or move between deployments.
- **Atomic credential editor** — `.env` is rewritten safely from the dashboard; comments + unknown keys preserved. Hot-reloads in-process.
- **Configurable branding** — set `FAMILY_NAME` in `.env` to brand the dashboard title, sidebar, and email subject fallback (e.g. `FAMILY_NAME=Smith` → "Smith Notifications").
- **Six-tab dashboard** — Members · Notifications · Logs · Family Tree · Schedule · Settings. Light + dark mode.
- **126-test suite** — unit + API integration tests, including DST, year-rollover, idempotency, and family-tree relationship invariants.

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
│         │            │  /api/branding         │  │
│         │            │  /health               │  │
│         ▼            └────────┬───────────────┘  │
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

Every notification flows through a single chokepoint (`app/utils/sender.py:execute_send`) which enforces idempotency. Adding a fourth channel (e.g. Pushover, ntfy, Discord) is one new file in `app/services/` plus a registration line in `app/main.py`.

See `CLAUDE.md` for the developer-facing architecture detail.

---

## Quick start

### Option A — one-shot installer (Raspberry Pi / Debian / Ubuntu)

Single command — clones the repo, creates the venv, installs deps, scaffolds `.env`, and installs the systemd unit:

```bash
curl -fsSL https://raw.githubusercontent.com/vertex-ai-automations/family-notification-system/master/install.sh | bash
```

Or with options (custom install location, port, branch):

```bash
curl -fsSL https://raw.githubusercontent.com/vertex-ai-automations/family-notification-system/master/install.sh \
  | TARGET_DIR=/opt/family-notifier PORT=8080 bash
```

Then edit `.env` and start the service:

```bash
$EDITOR /path/to/family-notification-system/.env
sudo systemctl start family-notifier
```

If you've already cloned the repo, just run `./install.sh` from inside it — the same script detects the existing checkout and skips the clone step.

The installer:
- clones `vertex-ai-automations/family-notification-system` (skipped when run from inside an existing checkout)
- creates `venv/` and installs `requirements.txt`
- copies `.env.example` → `.env` if missing
- substitutes the current user, repo path, and port into the systemd unit and installs it to `/etc/systemd/system/family-notifier.service`
- enables (but does not start) the service so you can edit `.env` first

Flags & env overrides: `PORT=8080`, `TARGET_DIR=/opt/family-notifier`, `BRANCH=v1.2.0`, `REPO_URL=…` for forks, and `--no-systemd` to skip the systemd step (for development / Docker / non-systemd hosts).

### Option B — manual

```bash
git clone https://github.com/vertex-ai-automations/family-notification-system.git
cd family-notification-system

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
$EDITOR .env                  # fill in real Twilio + SMTP credentials

uvicorn app.main:app --host 0.0.0.0 --port 8001
```

Then open `http://localhost:8001` (or `http://<pi-hostname>.local:8001` from another device on your network).

**Requirements:** Python 3.11+ (3.12 / 3.13 also tested). No native build dependencies — pure Python.

### Six dashboard tabs

- **Members** — add / edit / remove people, set parent + spouse relationships, see upcoming events
- **Notifications** — preview a rendered message per channel, send manually, pause/resume per person
- **Logs** — full history with filters and one-click retry of failed sends
- **Family Tree** — interactive tree across multiple clusters with a focus picker
- **Schedule** — change job times, advance-reminder windows, catch-up window, and channel toggles (live, no restart)
- **Settings** — Twilio + SMTP credentials, JSON import/export, log export & reset

---

## Configuration

### `.env` — credentials and deploy-time options

```ini
# Twilio (SMS + WhatsApp) — leave blank to disable
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_FROM_NUMBER=+15555550123
TWILIO_WHATSAPP_NUMBER=+14155238886   # Twilio WhatsApp sandbox; replace for production

# SMTP (Email) — leave blank to disable
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=you@example.com
SMTP_PASSWORD=your-app-password       # Gmail: create an App Password
SMTP_FROM_ADDRESS=you@example.com

# Optional
TZ=America/Chicago                    # IANA zone; default America/Chicago
FAMILY_NAME=Smith                     # default "Family"; brands dashboard + email subject
```

`PUT /api/credentials` (Settings page) rewrites `.env` atomically — comments and unrelated keys are preserved — then hot-reloads config. **No restart required for credential changes.** (Adding a brand-new channel still requires a restart so the service can be wired in.)

### `settings` table — schedule and channel toggles (live)

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

Schedule and channel-toggle changes apply **live** through `PUT /api/settings`.

---

## Data model

### `people`
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `name` | TEXT | Used for dedup on import |
| `phone` | TEXT | E.164, e.g. `+15555550100`. UI auto-prepends `+1` for 10-digit US |
| `email` | TEXT | Optional |
| `whatsapp` | TEXT | E.164. Stored `NULL` when same as phone — WhatsApp is skipped (not fallback) when not set |
| `birthday` | TEXT | `MM-DD` |
| `birth_year` | INTEGER | Optional, enables `{age}` template variable |
| `married` | BOOLEAN | When 0, anniversary fields are ignored |
| `spouse_name`, `anniversary`, `anniversary_year` | | Anniversary side; `anniversary` is `MM-DD` |
| `mother_id`, `father_id`, `spouse_id` | INTEGER FK → `people(id)` | Family-tree relationships. `ON DELETE SET NULL` |
| `custom_birthday_message`, `custom_anniversary_message` | TEXT | Templated; falls back to defaults when empty |
| `notifications_paused` | BOOLEAN | Pauses both advance reminders to others *and* same-day wishes |

Relationship invariants enforced by the API:
- A person cannot be their own ancestor (cycle detection on `mother_id` / `father_id`).
- `spouse_id` is bidirectional — setting it on one person syncs the inverse on the other.
- `_PATCH_ALLOWED` enforces an allowlist on dynamic UPDATEs.

### `notification_state` — idempotency
UNIQUE on `(person_id, event_type, trigger_type, channel, year_sent)`. Written **only on successful send**.

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
| `GET`  | `/health` | — | DB + per-service health |
| `GET`  | `/api/branding` | — | `{"family_name": "..."}` from `FAMILY_NAME` |
| `GET`  | `/api/members` | — | All members |
| `GET`  | `/api/members/upcoming` | — | Events in next 30 days |
| `GET`  | `/api/members/tree` | — | Nodes + parent/spouse edges for the family-tree page |
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
      "phone": "+15555550100",
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
      "phone": "5555550100",
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

Imports dedup by `name`. Family-tree relationship FKs (`mother_id`, `father_id`, `spouse_id`) are not exported/imported by reference; rebuild them from the dashboard after import.

---

## Running on a Raspberry Pi (systemd)

The included `systemd/family-notifier.service` is a *template* with three placeholders: `__USER__`, `__APP_DIR__`, `__PORT__`. The `install.sh` script substitutes them automatically. To do it by hand:

```bash
sudo sed \
  -e "s|__USER__|$(id -un)|g" \
  -e "s|__APP_DIR__|$(pwd)|g" \
  -e "s|__PORT__|8001|g" \
  systemd/family-notifier.service \
  | sudo tee /etc/systemd/system/family-notifier.service >/dev/null

sudo systemctl daemon-reload
sudo systemctl enable --now family-notifier.service
sudo systemctl status family-notifier.service
journalctl -u family-notifier.service -f
```

Default port is **8001** to avoid collision with other Pi services. RAM footprint: ~50–80 MB. The unit auto-starts on boot and restarts on crash.

---

## Testing

```bash
pytest                                                  # full suite (126 tests)
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
│   ├── main.py                  # FastAPI app + lifespan + service factory
│   ├── scheduler.py             # APScheduler jobs + reschedule + catch-up
│   ├── database.py              # SQLite schema, defaults, WAL, migrations
│   ├── models.py                # Pydantic models
│   ├── config.py                # .env loading + hot reload (incl. FAMILY_NAME)
│   ├── api/
│   │   ├── members.py           # CRUD + PATCH + upcoming + family tree
│   │   ├── notifications.py     # Preview / Send Now / Pause
│   │   ├── logs.py              # List + retry + export + reset
│   │   ├── settings.py          # Settings + credentials + import/export
│   │   └── health.py            # /health + /api/branding
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
│   └── static/                  # Dashboard SPA (HTML/CSS/JS, vendored D3 + family-chart)
├── data/
│   ├── family.db                # SQLite DB (gitignored)
│   └── exports/                 # JSON exports (gitignored)
├── tests/                       # pytest suite (126 tests)
├── systemd/family-notifier.service
├── install.sh                   # One-shot installer for Pi/Linux
├── requirements.txt
├── .env.example
└── pytest.ini
```

---

## Adding a new notification channel

To add e.g. Pushover or ntfy:

1. Create `app/services/pushover.py` with a class extending `NotificationService` (`name`, `enabled`, `send()`, `health_check()`). Have `send()` return `True` when the relevant contact field is empty (a *skip* is not a failure).
2. Add the contact field to the `people` table in `app/database.py:create_tables()` and to the Pydantic models in `app/models.py`.
3. Register the service in `app/main.py:_build_services()` — read its credentials from `app.config`, check the `<channel>_enabled` setting.
4. Add `<channel>_enabled` to `app/database.py:DEFAULTS`.
5. Restart. The new plugin gets the same idempotency, retry, and audit-trail behavior for free.

---

## Troubleshooting

**Service stuck in restart loop.** Probably another process owns the port — `journalctl -u family-notifier -n 30` will show `address already in use`. Either stop the other service, or re-run `PORT=8080 ./install.sh` (or edit the systemd unit) and `sudo systemctl daemon-reload && sudo systemctl restart family-notifier`.

**Dashboard shows the wrong app.** A different service on the same port answered first. See above.

**WhatsApp not sending despite person having a phone.** WhatsApp only sends when the person has an *explicit* WhatsApp number. Sending to plain phone numbers via the Twilio sandbox almost always fails and floods the log. Set `whatsapp` explicitly per person.

**Schedule changes don't seem to apply.** They should — the API live-reschedules. If you're on an older build that didn't, restart the service.

**Same-day "Send Now" is silently skipped on retry.** Same-day manual sends write a `notification_state` row to prevent the noon catch-up from double-sending. To test repeatedly, either use `7_day` / `1_day` triggers (which don't write state on manual send) or delete the state rows for that person.

**Family tree doesn't render / shows wrong layout.** Add at least one `mother_id` / `father_id` / `spouse_id` link via the member edit form. Use the focus picker if your family has multiple disjoint clusters.

---

## Security notes

- Credentials live exclusively in `.env`. Never in SQLite, never returned unmasked from the API.
- The dashboard has **no authentication** — assumes a trusted home network. **Do not expose port directly to the internet.** Use Tailscale / WireGuard / a VPN for remote access.
- The atomic `.env` writer preserves comments and unknown keys and avoids partial-write corruption.

---

## Acknowledgements

- [`family-chart`](https://github.com/donatso/family-chart) — MIT — interactive tree visualization
- [D3.js](https://d3js.org/) v7 — vendored
- [FastAPI](https://fastapi.tiangolo.com/), [APScheduler](https://apscheduler.readthedocs.io/), [Twilio Python SDK](https://www.twilio.com/docs/libraries/python)

## License

MIT — fork it, deploy it, customize it.
