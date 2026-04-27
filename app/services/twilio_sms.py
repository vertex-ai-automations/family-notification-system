import logging
from twilio.rest import Client
from app.services.base import NotificationService
from app.utils.retry import with_retry

logger = logging.getLogger(__name__)


class TwilioSMSService(NotificationService):
    name = "sms"

    def __init__(self, account_sid: str, auth_token: str, from_number: str):
        self._client = Client(account_sid, auth_token)
        self._from = from_number
        self.enabled = True

    def send(self, person: dict, message: str, **context) -> bool:
        self._reset()
        recipient = person.get("phone")
        if not recipient:
            self.last_skip = True
            return True
        try:
            with_retry(
                lambda: self._client.messages.create(to=recipient, from_=self._from, body=message),
                label=f"sms→{person.get('name')}",
            )
            return True
        except Exception as e:
            self.last_error = str(e)
            logger.warning("SMS send failed for %s: %s", person.get("name"), e)
            return False

    def health_check(self) -> bool:
        try:
            self._client.api.accounts(self._client.account_sid).fetch()
            return True
        except Exception:
            return False
