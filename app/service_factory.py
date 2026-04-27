from app.config import get_config
from app.database import get_connection
from app.services.twilio_sms import TwilioSMSService
from app.services.twilio_whatsapp import TwilioWhatsAppService
from app.services.email_smtp import EmailService


def build_services(db_path: str):
    """Build notification service instances from current config (.env) and DB settings.
    Called both at lifespan startup and after PUT /api/credentials or channel-toggle changes."""
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
