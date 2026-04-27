import logging
from twilio.rest import Client
from app.services.base import NotificationService
from app.utils.retry import with_retry

logger = logging.getLogger(__name__)


class TwilioWhatsAppService(NotificationService):
    name = "whatsapp"

    def __init__(self, account_sid: str, auth_token: str, from_number: str):
        self._client = Client(account_sid, auth_token)
        if from_number and not from_number.startswith("whatsapp:"):
            from_number = f"whatsapp:{from_number}"
        self._from = from_number
        self.enabled = True

    def send(self, person: dict, message: str, **context) -> bool:
        self._reset()
        # Skip silently when no explicit WhatsApp number — sending to plain phone
        # almost always fails Twilio sandbox rules and floods the failure log.
        number = person.get("whatsapp")
        if not number:
            self.last_skip = True
            return True
        to = f"whatsapp:{number}"
        try:
            with_retry(
                lambda: self._client.messages.create(to=to, from_=self._from, body=message),
                label=f"whatsapp→{person.get('name')}",
            )
            return True
        except Exception as e:
            self.last_error = str(e)
            logger.warning("WhatsApp send failed for %s: %s", person.get("name"), e)
            return False

    def health_check(self) -> bool:
        try:
            self._client.api.accounts(self._client.account_sid).fetch()
            return True
        except Exception:
            return False
