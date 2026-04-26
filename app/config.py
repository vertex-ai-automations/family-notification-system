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
        smtp_port=int(os.getenv("SMTP_PORT") or "587"),
        smtp_username=os.getenv("SMTP_USERNAME"),
        smtp_password=os.getenv("SMTP_PASSWORD"),
        smtp_from_address=os.getenv("SMTP_FROM_ADDRESS"),
    )
