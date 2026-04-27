import logging
import smtplib
from email.mime.text import MIMEText
from app.services.base import NotificationService
from app.utils.retry import with_retry

logger = logging.getLogger(__name__)


def _build_subject(person: dict, event_type: str, trigger_type: str, days: int) -> str:
    name = person.get("name") or "family"
    if event_type == "birthday":
        if trigger_type == "same_day":
            return f"Happy Birthday, {name}!"
        return f"Reminder: {name}'s birthday in {days} day(s)"
    if event_type == "anniversary":
        spouse = person.get("spouse_name") or ""
        suffix = f" {name} & {spouse}".rstrip()
        if trigger_type == "same_day":
            return f"Happy Anniversary,{suffix}!"
        return f"Reminder:{suffix}'s anniversary in {days} day(s)"
    return "NoorFamily Notification"


class EmailService(NotificationService):
    name = "email"

    def __init__(self, host: str, port: int, username: str, password: str, from_address: str):
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._from = from_address
        self.enabled = True

    def send(self, person: dict, message: str, **context) -> bool:
        self._reset()
        recipient = person.get("email")
        if not recipient:
            self.last_skip = True
            return True
        subject = _build_subject(
            person,
            context.get("event_type", ""),
            context.get("trigger_type", ""),
            int(context.get("days", 0)),
        )
        try:
            def _do_send():
                msg = MIMEText(message)
                msg["Subject"] = subject
                msg["From"] = self._from
                msg["To"] = recipient
                with smtplib.SMTP(self._host, self._port) as server:
                    server.starttls()
                    server.login(self._username, self._password)
                    server.sendmail(self._from, recipient, msg.as_string())
            with_retry(_do_send, label=f"email→{person.get('name')}")
            return True
        except Exception as e:
            self.last_error = str(e)
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
