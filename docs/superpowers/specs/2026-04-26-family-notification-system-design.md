# Family Notification System — Design Spec
**Date:** 2026-04-26
**Target Platform:** Raspberry Pi 5 (home network deployment)

---

## Overview

A self-hosted family notification system that sends birthday and anniversary reminders and wishes via SMS, WhatsApp, and Email. Managed through a local web dashboard accessible from any device on the home network. Designed to replace two standalone Python/Twilio scripts with a unified, scalable, and maintainable system.

---

## Goals

- Add, edit, and remove family members with contact info and custom messages through a UI — no manual JSON editing
- Send advance reminders to family members (7-day and 1-day before) and same-day personal wishes
- Support SMS, WhatsApp, and Email via a plugin architecture that makes adding new channels a one-file change
- Log all notification activity with per-send status and retry on failure
- Run reliably on a Pi 5 with auto-start on boot and no manual intervention
- Store credentials securely in a `.env` file — never hardcoded in source

---

## Non-Goals (for now)

- OpenAI / AI-generated messages (intentionally deferred, can be added as a plugin later)
- Authentication / login (open on trusted home network)
- Mobile app or push notifications
- Multi-family / multi-admin support

---

## Architecture

**Stack:** FastAPI (Python) + APScheduler + SQLite + plain HTML/CSS/JS frontend

**Single process** managed by systemd. FastAPI serves both the REST API and the static dashboard frontend. APScheduler runs inside the FastAPI process. SQLite is the single source of truth.

```
family-notification-system/
├── app/
│   ├── main.py                  # FastAPI app entry point
│   ├── scheduler.py             # APScheduler setup & job registration
│   ├── database.py              # SQLite connection, migrations
│   ├── models.py                # Pydantic + SQLite models
│   ├── config.py                # Loads .env credentials
│   │
│   ├── services/                # Notification plugin system
│   │   ├── base.py              # Abstract NotificationService interface
│   │   ├── twilio_sms.py        # SMS plugin
│   │   ├── twilio_whatsapp.py   # WhatsApp plugin
│   │   └── email_smtp.py        # Email plugin
│   │
│   ├── api/                     # FastAPI route handlers
│   │   ├── members.py           # CRUD for family members
│   │   ├── notifications.py     # Manual trigger, preview, pause/resume
│   │   ├── logs.py              # Notification history
│   │   └── settings.py          # Timing config, credentials
│   │
│   └── static/                  # Dashboard frontend
│       ├── index.html
│       ├── app.js
│       └── style.css
│
├── data/
│   ├── family.db                # SQLite database
│   └── exports/                 # JSON export output
│
├── .env                         # Credentials (never committed)
├── .env.example                 # Template with placeholder values
├── requirements.txt
└── systemd/
    └── family-notifier.service  # systemd unit for Pi
```

---

## Data Model

### `people` table
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | Auto-increment |
| name | TEXT | Full name |
| phone | TEXT | E.164 format e.g. `+17188790062`, optional |
| email | TEXT | Optional |
| whatsapp | TEXT | E.164 format; stored as NULL if same as phone (resolved to phone at send time) |
| birthday | TEXT | MM-DD format |
| birth_year | INTEGER | Optional, enables `{age}` variable |
| married | BOOLEAN | Default false; anniversary fields only processed when true |
| spouse_name | TEXT | Optional |
| anniversary | TEXT | MM-DD format, optional |
| anniversary_year | INTEGER | Optional, enables `{years_married}` variable |
| custom_birthday_message | TEXT | Supports template variables; falls back to default if empty |
| custom_anniversary_message | TEXT | Supports template variables; falls back to default if empty |
| notifications_paused | BOOLEAN | Default false |
| created_at | DATETIME | |
| updated_at | DATETIME | |

**Phone number format:** All phone numbers stored in E.164 format (`+1XXXXXXXXXX` for US). The UI accepts 10-digit US numbers and auto-prepends `+1`. Non-US numbers must be entered with the full country code.

**WhatsApp field rule:** Store `NULL` when WhatsApp number is the same as phone. At send time, the WhatsApp plugin resolves: use `whatsapp` if set, else fall back to `phone`.

**`married` field:** When `married = false`, anniversary processing is skipped entirely regardless of whether `anniversary` is populated.

### `notification_state` table
Prevents duplicate sends within the same calendar year. Keyed per person + event + trigger + channel so a failure on one channel does not block retry on that channel while still preventing re-sends on successful channels.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| person_id | INTEGER FK | |
| event_type | TEXT | `birthday` or `anniversary` |
| trigger_type | TEXT | `7_day`, `1_day`, or `same_day` |
| channel | TEXT | `sms`, `whatsapp`, or `email` |
| year_sent | INTEGER | Resets naturally each new year |
| sent_at | DATETIME | |

**Unique constraint:** `(person_id, event_type, trigger_type, channel, year_sent)`

**Write rule:** A state row is written only after a successful send on that channel. Failed sends are logged but do not write a state row, enabling retry.

### `notification_log` table
Permanent history of every send attempt.

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| person_id | INTEGER FK | |
| event_type | TEXT | `birthday` or `anniversary` |
| trigger_type | TEXT | `7_day`, `1_day`, or `same_day` |
| channel | TEXT | `sms`, `whatsapp`, or `email` |
| message_body | TEXT | Rendered final message |
| status | TEXT | `sent` or `failed` |
| error_message | TEXT | Populated on failure |
| sent_at | DATETIME | |

### `settings` table
Key/value store for timing and channel configuration. Credentials are never stored here.

| Key | Default | Description |
|---|---|---|
| advance_days_week | 7 | Days before for week-ahead reminder |
| advance_days_day | 1 | Days before for day-before reminder |
| job1_time | 08:00 | Daily run time for advance reminders |
| job2_time | 12:00 | Daily run time for same-day wishes |
| catch_up_hours | 6 | Hours after job2_time to still send missed same-day wishes |
| sms_enabled | true | Global SMS toggle |
| whatsapp_enabled | true | Global WhatsApp toggle |
| email_enabled | true | Global Email toggle |

**Timing change rule:** Changing `advance_days_week` or `advance_days_day` mid-year only affects future checks. It does not retroactively invalidate or re-fire notifications already sent or skipped in the current year.

### Credentials
All credentials live exclusively in `.env`. The Settings UI reads masked values from the running config (not from the DB) and writes changes back to `.env`, then triggers a config hot-reload without restarting the process. This keeps credentials out of the database.

```
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_FROM_NUMBER=
TWILIO_WHATSAPP_NUMBER=
SMTP_HOST=
SMTP_PORT=
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_FROM_ADDRESS=
```

### Default Messages
Used when a person's custom message field is empty. Advance reminders use a single configurable-aware template with `{days}` so they remain correct regardless of the `advance_days_week` / `advance_days_day` settings:

- **Birthday advance reminder (to others):** `"NoorFamily Reminder: {name}'s birthday is in {days} day(s)! Don't forget to wish them!"`
- **Birthday same-day wish (to person):** `"Happy Birthday, {name}! Wishing you joy and happiness today!"`
- **Anniversary advance reminder (to others):** `"NoorFamily Reminder: {name} & {spouse}'s anniversary is in {days} day(s)!"`
- **Anniversary same-day wish (to person):** `"Happy Anniversary, {name} & {spouse}! Wishing you many more years of happiness together!"`

### Template Variables
Available in `custom_birthday_message`, `custom_anniversary_message`, and default messages:

| Variable | Resolves to |
|---|---|
| `{name}` | Person's name |
| `{age}` | Calculated from birth_year (omitted if birth_year not set) |
| `{spouse}` | Spouse name |
| `{years_married}` | Calculated from anniversary_year (omitted if not set) |
| `{day_of_week}` | e.g., "Monday" |
| `{days}` | Integer days until event — always available in all message contexts; resolves to `1` on day-before, `0` on same-day |

---

## Notification Plugin System

All services implement a common interface. The `send()` method receives the full person object and message string — each plugin is responsible for extracting the correct contact field (`person.phone`, `person.email`, etc.):

```python
class NotificationService:
    name: str        # "sms", "whatsapp", "email"
    enabled: bool

    def send(self, person: Person, message: str) -> bool: ...
    def health_check(self) -> bool: ...
```

Each plugin selects its own contact field:
- `TwilioSMSService` reads `person.phone`
- `TwilioWhatsAppService` reads `person.whatsapp or person.phone`
- `EmailService` reads `person.email`

If the relevant contact field is empty or None, the plugin logs a skip (not a failure) and returns `True` (no error, just nothing to send).

**Notification flow:**
1. APScheduler fires job
2. For each person with event today (or N days away): check `notification_state` per channel — already sent this year for this trigger + channel? Skip that channel.
3. Build message — apply template variables to custom message (or use default)
4. For each enabled service where contact field is populated: call `service.send(person, message)`
5. Write result to `notification_log` (status: sent or failed)
6. On success only: write to `notification_state` for that channel (marks done for this year)

**Adding a new channel** = create one new file in `services/` implementing the base class. Register it in `main.py`. Nothing else changes.

---

## Scheduler

Three logical triggers handled by two APScheduler jobs:

### Job 1 — Advance Reminders (default: 8:00 AM daily)
Runs one daily job that checks both advance windows (`7_day` and `1_day`) in a single pass. For each person, checks if their birthday or anniversary falls exactly `advance_days_week` or `advance_days_day` days from today.

- **Recipients:** All OTHER family members (not the person whose event it is)
- **Channels used:** Each recipient's own enabled channels (SMS if they have phone, email if they have email, etc.)
- **Trigger types written to state:** `7_day` and `1_day` (tracked separately)
- **Catch-up:** Not applicable. Advance reminders that are missed (Pi offline) are skipped — better to miss a week-ahead alert than send a stale one.

### Job 2 — Day-of Wishes (default: 12:00 PM daily)
Sends the personal greeting directly to the person whose event falls today.

- **Recipients:** Only the person whose event it is today
- **Channels used:** The person's own enabled channels
- **Trigger type written to state:** `same_day`
- **Catch-up:** If the Pi was offline and restarts within `catch_up_hours` of `job2_time`, the job fires immediately (via APScheduler `misfire_grace_time`). If a `notification_state` row already exists for `same_day` this year on that channel (e.g., from a manual send), the catch-up is skipped for that channel only.

Both jobs are idempotent — safe to restart mid-day without duplicate sends.

---

## Dashboard UI

Served at `http://raspberrypi.local:8000`. Five sections in sidebar nav:

### Members
- Table: name, birthday, anniversary, channel icons (SMS/WhatsApp/Email — greyed out if no contact info), paused badge
- Add / Edit / Remove actions
- Edit form: all fields including custom messages, pause toggle
- Phone input: accepts 10-digit US format, auto-converts to E.164 on save
- Upcoming events panel: next 30 days

### Notifications
- Select person + event type (birthday / anniversary) + trigger type (7-day / 1-day / same-day)
- Preview: renders exact final message per channel before sending
- Send Now: immediately fires to all enabled channels for that person; bypasses `notification_state` check (manual overrides are always allowed); writes to `notification_log`. For `same_day` trigger type, also writes a `notification_state` row per channel (preventing a duplicate from Job 2's catch-up on the same day). For `7_day` and `1_day` trigger types, does NOT write a state row (so scheduled advance reminders still fire on their normal day).
- Per-person pause/resume toggle

### Logs
- Filterable table: person, channel, event type, trigger type, date range, status (sent/failed)
- Failed rows show error message inline
- One-click retry: re-attempts only the failed channel for that specific log row; bypasses `notification_state` check for that channel only

### Schedule
- Edit advance reminder days (week-before and day-before windows)
- Edit job run times
- Edit catch-up window
- Enable/disable channels globally

### Settings
- Twilio SID, Auth Token, From number (masked by default, click to reveal and edit)
- WhatsApp number
- SMTP host, port, username, password, from address (masked)
- Save writes back to `.env` and hot-reloads config
- Export to JSON (`data/exports/family_YYYY-MM-DD.json`)
- Import from JSON (bulk-load; deduplicates by name)

### JSON Export Schema
```json
{
  "exported_at": "YYYY-MM-DD",
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
      "custom_birthday_message": "Happy Birthday {name}!",
      "custom_anniversary_message": "",
      "notifications_paused": false
    }
  ]
}
```

---

## Migration from Existing Scripts

1. Import `dates_family.json` and `dates_all.json` via the JSON import feature on first run
2. The importer deduplicates by name and merges phone/married/anniversary fields
3. Phone numbers are auto-converted to E.164 format during import
4. Existing `notified_week_before` / `notified_day_before` flags: if `true`, a corresponding `notification_state` row is written with `year_sent = current year` and `channel = sms` only (matching the old scripts' SMS-only behavior). This leaves `whatsapp` and `email` channels uncovered so they can send fresh on the new system. If `false`, no state row is written and the scheduler sends normally.
5. Old scripts (`alert_with_twilio.py`, `alert_with_twilio_1200.py`) are retired — replaced by Job 1 and Job 2

---

## Security

- All credentials stored in `.env`, loaded via `python-dotenv` at startup
- `.env` is gitignored — `.env.example` is committed with placeholder values
- Dashboard has no authentication (trusted home network assumption)
- SQLite file stored at `data/family.db` with OS-level file permissions (Pi user only)
- Credentials never stored in SQLite

---

## Raspberry Pi 5 Deployment

- Python 3.11+ (available on Pi OS Bookworm)
- `systemd` unit in `systemd/family-notifier.service` auto-starts on boot, restarts on crash
- APScheduler `misfire_grace_time` set to `catch_up_hours * 3600` for Job 2
- Accessible at `http://raspberrypi.local:8000` from any device on the home network
- SQLite requires no separate database server process
- Total RAM footprint: ~50-80MB

---

## Future Extensions (not in scope now)

- OpenAI GPT message generation (new plugin, no architecture changes needed)
- Push notifications via ntfy or Pushover (new service plugin)
- Login/authentication if moved outside home network
- Group family chat notifications (WhatsApp group support via Twilio)
