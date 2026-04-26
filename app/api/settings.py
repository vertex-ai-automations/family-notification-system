import os
import sqlite3
from typing import Dict, Optional
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from app.api.deps import get_db

router = APIRouter(prefix="/api", tags=["settings"])

@router.get("/settings")
def get_settings(db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute("SELECT key, value FROM settings").fetchall()
    return {r["key"]: r["value"] for r in rows}

@router.put("/settings")
def update_settings(updates: Dict[str, str], db: sqlite3.Connection = Depends(get_db)):
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
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, _, v = line.partition("=")
                    existing[k.strip()] = v.strip()
    for k, v in mapping.items():
        if v is not None:
            existing[k] = v
    with open(env_path, "w") as f:
        for k, v in existing.items():
            f.write(f"{k}={v}\n")
    from app.config import hot_reload
    hot_reload()
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
