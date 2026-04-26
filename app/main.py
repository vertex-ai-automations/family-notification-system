import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.database import init_db
from app.config import get_config
from app.api import members, notifications, logs, settings as settings_api
from app.api.deps import set_db_path

def _build_services(db_path: str):
    """Build notification service instances from current config and DB settings."""
    import sqlite3
    from app.database import get_connection
    from app.services.twilio_sms import TwilioSMSService
    from app.services.twilio_whatsapp import TwilioWhatsAppService
    from app.services.email_smtp import EmailService

    cfg = get_config()
    conn = get_connection(db_path)
    sms_on = conn.execute("SELECT value FROM settings WHERE key='sms_enabled'").fetchone()
    wa_on = conn.execute("SELECT value FROM settings WHERE key='whatsapp_enabled'").fetchone()
    email_on = conn.execute("SELECT value FROM settings WHERE key='email_enabled'").fetchone()
    conn.close()

    services = []
    if cfg.twilio_account_sid and cfg.twilio_auth_token:
        sms = TwilioSMSService(cfg.twilio_account_sid, cfg.twilio_auth_token, cfg.twilio_from_number or "")
        sms.enabled = sms_on is None or sms_on[0] == "true"
        services.append(sms)

        wa_from = cfg.twilio_whatsapp_number or ""
        wa = TwilioWhatsAppService(cfg.twilio_account_sid, cfg.twilio_auth_token, wa_from)
        wa.enabled = wa_on is None or wa_on[0] == "true"
        services.append(wa)

    if cfg.smtp_host and cfg.smtp_username:
        email = EmailService(
            cfg.smtp_host, cfg.smtp_port,
            cfg.smtp_username, cfg.smtp_password or "",
            cfg.smtp_from_address or ""
        )
        email.enabled = email_on is None or email_on[0] == "true"
        services.append(email)

    return services

def create_app(db_path: str = "data/family.db", start_scheduler: bool = True) -> FastAPI:
    set_db_path(db_path)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        init_db(db_path)
        if start_scheduler:
            services = _build_services(db_path)
            from app.scheduler import setup_scheduler
            setup_scheduler(services, db_path)
        yield
        if start_scheduler:
            from app.scheduler import stop_scheduler
            stop_scheduler()

    app = FastAPI(title="Family Notification System", lifespan=lifespan)
    app.include_router(members.router)
    app.include_router(notifications.router)
    app.include_router(logs.router)
    app.include_router(settings_api.router)

    static_dir = os.path.join(os.path.dirname(__file__), "static")
    if os.path.exists(static_dir) and os.listdir(static_dir):
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

    return app

app = create_app()
