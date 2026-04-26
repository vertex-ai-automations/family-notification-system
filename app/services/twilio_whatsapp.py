from twilio.rest import Client
from app.services.base import NotificationService


class TwilioWhatsAppService(NotificationService):
    name = "whatsapp"

    def __init__(self, account_sid: str, auth_token: str, from_number: str):
        self._client = Client(account_sid, auth_token)
        self._from = from_number
        self.enabled = True

    def send(self, person: dict, message: str) -> bool:
        number = person.get("whatsapp") or person.get("phone")
        if not number:
            return True
        to = f"whatsapp:{number}"
        try:
            self._client.messages.create(to=to, from_=self._from, body=message)
            return True
        except Exception as e:
            print(f"WhatsApp send failed for {person.get('name')}: {e}")
            return False

    def health_check(self) -> bool:
        try:
            self._client.api.accounts(self._client.account_sid).fetch()
            return True
        except Exception:
            return False
