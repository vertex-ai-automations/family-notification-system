import logging
from twilio.rest import Client
from app.services.base import NotificationService

logger = logging.getLogger(__name__)


class TwilioSMSService(NotificationService):
    name = "sms"

    def __init__(self, account_sid: str, auth_token: str, from_number: str):
        self._client = Client(account_sid, auth_token)
        self._from = from_number
        self.enabled = True

    def send(self, person: dict, message: str) -> bool:
        recipient = person.get("phone")
        if not recipient:
            return True
        try:
            self._client.messages.create(to=recipient, from_=self._from, body=message)
            return True
        except Exception as e:
            logger.warning("SMS send failed for %s: %s", person.get("name"), e)
            return False

    def health_check(self) -> bool:
        try:
            self._client.api.accounts(self._client.account_sid).fetch()
            return True
        except Exception:
            return False
