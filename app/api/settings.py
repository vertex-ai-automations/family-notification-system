import os
import re
import sqlite3
import tempfile
from typing import Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from app.api.deps import get_db, _db_path_value

router = APIRouter(prefix="/api", tags=["settings"])


# Allowed settings keys + per-key validators. Reject unknown or malformed input
# at the API boundary so a typo can't silently crash the scheduler at restart.
_TIME_RE = re.compile(r"^([01]?\d|2[0-3]):[0-5]\d$")

def _validate_setting(key: str, value: str) -> str:
    if key in ("job1_time", "job2_time"):
        if not _TIME_RE.match(value):
            raise HTTPException(400, f"{key} must be HH:MM (24-hour)")
        return value
    if key in ("advance_days_week", "advance_days_day"):
        try:
            n = int(value)
        except ValueError:
            raise HTTPException(400, f"{key} must be an integer")
        if not 0 <= n <= 365:
            raise HTTPException(400, f"{key} must be between 0 and 365")
        return str(n)
    if key == "catch_up_hours":
        try:
            n = int(value)
        except ValueError:
            raise HTTPException(400, f"{key} must be an integer")
        if not 0 <= n <= 24:
            raise HTTPException(400, f"{key} must be between 0 and 24")
        return str(n)
    if key in ("sms_enabled", "whatsapp_enabled", "email_enabled"):
        if value not in ("true", "false"):
            raise HTTPException(400, f"{key} must be 'true' or 'false'")
        return value
    raise HTTPException(400, f"Unknown setting key: {key}")


@router.get("/settings")
def get_settings(db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute("SELECT key, value FROM settings").fetchall()
    return {r["key"]: r["value"] for r in rows}


@router.put("/settings")
def update_settings(updates: Dict[str, str], db: sqlite3.Connection = Depends(get_db)):
    validated = {k: _validate_setting(k, v) for k, v in updates.items()}
    for key, value in validated.items():
        db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (key, value))
    db.commit()
    # Live apply: channel toggles + Twilio creds = service rebuild; timing keys = reschedule.
    if any(k.endswith("_enabled") for k in validated):
        from app.service_factory import build_services
        from app.scheduler import set_services
        set_services(build_services(_db_path_value()))
    if any(k in validated for k in ("job1_time", "job2_time", "catch_up_hours")):
        from app.scheduler import reschedule_jobs
        reschedule_jobs()
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


_ENV_KEY_MAP = {
    "twilio_account_sid": "TWILIO_ACCOUNT_SID",
    "twilio_auth_token": "TWILIO_AUTH_TOKEN",
    "twilio_from_number": "TWILIO_FROM_NUMBER",
    "twilio_whatsapp_number": "TWILIO_WHATSAPP_NUMBER",
    "smtp_host": "SMTP_HOST",
    "smtp_port": "SMTP_PORT",
    "smtp_username": "SMTP_USERNAME",
    "smtp_password": "SMTP_PASSWORD",
    "smtp_from_address": "SMTP_FROM_ADDRESS",
}


def _write_env_atomic(env_path: str, updates: dict[str, str]):
    """Read existing .env line-by-line, replace touched keys in place, append new ones,
    preserve comments + blank lines, and write atomically via tmp + os.replace."""
    lines: list[str] = []
    seen: set[str] = set()
    if os.path.exists(env_path):
        with open(env_path) as f:
            for raw in f:
                stripped = raw.strip()
                if not stripped or stripped.startswith("#") or "=" not in stripped:
                    lines.append(raw.rstrip("\n"))
                    continue
                k, _, _ = stripped.partition("=")
                k = k.strip()
                if k in updates:
                    lines.append(f"{k}={updates[k]}")
                    seen.add(k)
                else:
                    lines.append(raw.rstrip("\n"))
    for k, v in updates.items():
        if k not in seen:
            lines.append(f"{k}={v}")

    dir_name = os.path.dirname(os.path.abspath(env_path)) or "."
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, prefix=".env.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            f.write("\n".join(lines) + "\n")
        os.replace(tmp_path, env_path)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


@router.put("/credentials")
def update_credentials(creds: CredentialUpdate):
    payload = creds.model_dump(exclude_none=True)
    env_updates: dict[str, str] = {}
    for field, value in payload.items():
        env_key = _ENV_KEY_MAP[field]
        env_updates[env_key] = str(value)
    if env_updates:
        _write_env_atomic(".env", env_updates)
    from app.config import hot_reload
    hot_reload()
    # Rebuild service instances so the running app picks up new credentials.
    from app.service_factory import build_services
    from app.scheduler import set_services
    set_services(build_services(_db_path_value()))
    return {"status": "updated"}


@router.post("/import")
async def import_data(request: Request, db: sqlite3.Connection = Depends(get_db)):
    from app.utils.migration import import_json
    body = await request.json()
    return import_json(body, db)


@router.get("/export")
def export_data(db: sqlite3.Connection = Depends(get_db)):
    import datetime
    from app.utils.migration import export_json
    data = export_json(db)
    filename = f"family_{datetime.date.today().isoformat()}.json"
    return JSONResponse(content=data, headers={"Content-Disposition": f"attachment; filename={filename}"})
