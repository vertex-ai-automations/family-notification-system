from unittest.mock import MagicMock, patch
from app.services.base import NotificationService, ServiceRegistry


class MockService(NotificationService):
    name = "mock"
    def send(self, person, message):
        return True
    def health_check(self):
        return True


def test_registry_returns_enabled_services():
    svc = MockService()
    svc.enabled = True
    registry = ServiceRegistry([svc])
    assert registry.get_enabled() == [svc]


def test_registry_excludes_disabled():
    svc = MockService()
    svc.enabled = False
    registry = ServiceRegistry([svc])
    assert registry.get_enabled() == []


# --- Task 7: Twilio SMS ---

from app.services.twilio_sms import TwilioSMSService


def test_sms_sends_to_phone():
    with patch("app.services.twilio_sms.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        svc = TwilioSMSService("AC123", "tok", "+10000000000")
        result = svc.send({"name": "John", "phone": "+17188790062"}, "Happy Birthday!")
        assert result is True
        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["to"] == "+17188790062"


def test_sms_skips_person_with_no_phone():
    with patch("app.services.twilio_sms.Client"):
        svc = TwilioSMSService("AC123", "tok", "+10000000000")
        assert svc.send({"name": "John", "phone": None}, "msg") is True


def test_sms_returns_false_on_twilio_error():
    with patch("app.services.twilio_sms.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("Twilio error")
        mock_client_cls.return_value = mock_client
        svc = TwilioSMSService("AC123", "tok", "+10000000000")
        assert svc.send({"name": "John", "phone": "+17188790062"}, "msg") is False


# --- Task 8: Twilio WhatsApp ---

from app.services.twilio_whatsapp import TwilioWhatsAppService


def test_whatsapp_uses_whatsapp_field_when_set():
    with patch("app.services.twilio_whatsapp.Client") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        svc = TwilioWhatsAppService("AC123", "tok", "whatsapp:+14155238886")
        svc.send({"name": "John", "phone": "+17188790062", "whatsapp": "+19998887777"}, "msg")
        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["to"] == "whatsapp:+19998887777"


def test_whatsapp_falls_back_to_phone():
    with patch("app.services.twilio_whatsapp.Client") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        svc = TwilioWhatsAppService("AC123", "tok", "whatsapp:+14155238886")
        svc.send({"name": "John", "phone": "+17188790062", "whatsapp": None}, "msg")
        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["to"] == "whatsapp:+17188790062"


# --- Task 9: Email SMTP ---

from app.services.email_smtp import EmailService


def test_email_sends_to_email_field():
    with patch("app.services.email_smtp.smtplib.SMTP") as mock_smtp_cls:
        mock_smtp = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_smtp)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
        svc = EmailService("smtp.gmail.com", 587, "user@test.com", "pass", "user@test.com")
        result = svc.send({"name": "John", "email": "john@example.com"}, "Happy Birthday!")
        assert result is True
        mock_smtp.sendmail.assert_called_once()


def test_email_skips_person_with_no_email():
    svc = EmailService("smtp.gmail.com", 587, "user@test.com", "pass", "user@test.com")
    assert svc.send({"name": "John", "email": None}, "msg") is True


def test_whatsapp_skips_person_with_no_contact():
    with patch("app.services.twilio_whatsapp.Client"):
        svc = TwilioWhatsAppService("AC123", "tok", "whatsapp:+14155238886")
        result = svc.send({"name": "John", "phone": None, "whatsapp": None}, "msg")
        assert result is True


def test_email_returns_false_on_smtp_error():
    with patch("app.services.email_smtp.smtplib.SMTP") as mock_smtp_cls:
        mock_smtp_cls.side_effect = Exception("SMTP connection failed")
        svc = EmailService("smtp.gmail.com", 587, "user@test.com", "pass", "user@test.com")
        result = svc.send({"name": "John", "email": "john@example.com"}, "msg")
        assert result is False
