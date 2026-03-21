import asyncio
import logging
from typing import Dict, Any

import requests

from config import settings

logger = logging.getLogger(__name__)

# WhatsApp Cloud API base URL (use your own WhatsApp Business number)
WHATSAPP_API_BASE = "https://graph.facebook.com/v21.0"


class WhatsAppService:
    """Service for sending WhatsApp messages.
    Supports three backends: mock, twilio (sandbox), and meta (Cloud API).
    Set WHATSAPP_BACKEND env var to choose: 'mock' | 'twilio' | 'meta'
    """

    def __init__(self):
        self.backend = getattr(settings, "WHATSAPP_BACKEND", "mock").lower()

        # Legacy fallback: if WHATSAPP_MOCK_MODE is explicitly set but WHATSAPP_BACKEND isn't
        if self.backend == "mock" and not getattr(settings, "WHATSAPP_MOCK_MODE", True):
            self.backend = "meta"

        # Meta Cloud API config
        self.api_token = getattr(settings, "WHATSAPP_API_TOKEN", "") or ""
        self.phone_number_id = getattr(settings, "WHATSAPP_PHONE_NUMBER_ID", "") or ""

        # Twilio config
        self.twilio_sid = getattr(settings, "TWILIO_ACCOUNT_SID", "") or ""
        self.twilio_token = getattr(settings, "TWILIO_AUTH_TOKEN", "") or ""
        self.twilio_from = getattr(settings, "TWILIO_WHATSAPP_NUMBER", "") or "whatsapp:+14155238886"

        self._twilio_client = None

        logger.info("WhatsAppService initialised with backend=%s", self.backend)

    def _get_twilio_client(self):
        if self._twilio_client is None:
            from twilio.rest import Client
            self._twilio_client = Client(self.twilio_sid, self.twilio_token)
        return self._twilio_client

    async def send_message(self, to_phone: str, message: str) -> Dict[str, Any]:
        """Send a WhatsApp message using the configured backend."""
        if self.backend == "twilio":
            return await self._send_twilio(to_phone, message)
        elif self.backend == "meta":
            return await self._send_meta(to_phone, message)
        else:
            return await self._send_mock(to_phone, message)

    async def _send_mock(self, to_phone: str, message: str) -> Dict[str, Any]:
        logger.info("[MOCK WhatsApp] To: %s", to_phone)
        logger.info("[MOCK WhatsApp] Message: %s", message[:200])
        logger.info("=" * 80)
        return {"status": "mock_sent", "to": to_phone, "message": message}

    async def _send_twilio(self, to_phone: str, message: str) -> Dict[str, Any]:
        """Send via Twilio WhatsApp (sandbox or production)."""
        if not self.twilio_sid or not self.twilio_token:
            logger.error("Twilio not configured: set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN")
            return {"status": "error", "message": "Twilio not configured"}

        # Ensure the 'to' number has the whatsapp: prefix
        to_formatted = to_phone if to_phone.startswith("whatsapp:") else f"whatsapp:{to_phone}"
        # Ensure + prefix on the number portion
        if "whatsapp:+" not in to_formatted:
            to_formatted = to_formatted.replace("whatsapp:", "whatsapp:+")

        def _send():
            client = self._get_twilio_client()
            return client.messages.create(
                body=message,
                from_=self.twilio_from,
                to=to_formatted,
            )

        try:
            twilio_msg = await asyncio.to_thread(_send)
            logger.info("Twilio WhatsApp sent to %s (sid=%s)", to_formatted, twilio_msg.sid)
            return {"status": "sent", "to": to_formatted, "sid": twilio_msg.sid}
        except Exception as e:
            logger.exception("Twilio send failed: %s", e)
            return {"status": "error", "message": str(e)}

    async def _send_meta(self, to_phone: str, message: str) -> Dict[str, Any]:
        """Send via Meta WhatsApp Cloud API."""
        if not self.api_token or not self.phone_number_id:
            logger.error("WhatsApp Cloud API not configured: set WHATSAPP_API_TOKEN and WHATSAPP_PHONE_NUMBER_ID")
            return {"status": "error", "message": "WhatsApp not configured"}

        to_digits = to_phone.replace("whatsapp:", "").strip().lstrip("+")

        url = f"{WHATSAPP_API_BASE}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_digits,
            "type": "text",
            "text": {"body": message},
        }

        def _post():
            return requests.post(url, headers=headers, json=payload, timeout=15)

        try:
            response = await asyncio.to_thread(_post)
            data = response.json()
            if response.status_code >= 400:
                logger.warning("WhatsApp API error: %s %s", response.status_code, data)
                return {"status": "error", "code": response.status_code, "body": data}
            logger.info("WhatsApp sent to %s", to_digits)
            return {"status": "sent", "to": to_digits, "response": data}
        except Exception as e:
            logger.exception("WhatsApp send failed: %s", e)
            return {"status": "error", "message": str(e)}
