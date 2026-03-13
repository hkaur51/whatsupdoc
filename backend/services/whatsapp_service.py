import asyncio
import logging
from typing import Dict, Any

import requests

from config import settings

logger = logging.getLogger(__name__)

# WhatsApp Cloud API base URL (use your own WhatsApp Business number)
WHATSAPP_API_BASE = "https://graph.facebook.com/v21.0"


class WhatsAppService:
    """Service for sending WhatsApp messages via Meta WhatsApp Cloud API.
    Use with a purchased/registered WhatsApp Business number and its credentials.
    """

    def __init__(self):
        self.mock_mode = getattr(settings, "WHATSAPP_MOCK_MODE", True)
        self.api_token = getattr(settings, "WHATSAPP_API_TOKEN", "") or ""
        self.phone_number_id = getattr(settings, "WHATSAPP_PHONE_NUMBER_ID", "") or ""

    async def send_message(self, to_phone: str, message: str) -> Dict[str, Any]:
        """Send a WhatsApp message. When mock is off, uses WhatsApp Cloud API."""
        if self.mock_mode:
            logger.info("[MOCK WhatsApp] To: %s", to_phone)
            logger.info("[MOCK WhatsApp] Message: %s", message[:200])
            logger.info("=" * 80)
            return {"status": "mock_sent", "to": to_phone, "message": message}

        if not self.api_token or not self.phone_number_id:
            logger.error("WhatsApp Cloud API not configured: set WHATSAPP_API_TOKEN and WHATSAPP_PHONE_NUMBER_ID")
            return {"status": "error", "message": "WhatsApp not configured"}

        # Strip "whatsapp:" or country code prefix for API (API expects digits only, no +)
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
