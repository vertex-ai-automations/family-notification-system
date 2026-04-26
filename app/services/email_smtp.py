import logging
import smtplib
from email.mime.text import MIMEText
from app.services.base import NotificationService

logger = logging.getLogger(__name__)


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
            msg["Subject"] = f"NoorFamily — {message[:40]}"
            msg["From"] = self._from
            msg["To"] = recipient
            with smtplib.SMTP(self._host, self._port) as server:
                server.starttls()
                server.login(self._username, self._password)
                server.sendmail(self._from, recipient, msg.as_string())
            return True
        except Exception as e:
            logger.warning("Email send failed for %s: %s", person.get("name"), e)
            return False

    def health_check(self) -> bool:
        try:
            with smtplib.SMTP(self._host, self._port, timeout=5) as server:
                server.ehlo()
                server.starttls()
                server.login(self._username, self._password)
            return True
        except Exception:
            return False
