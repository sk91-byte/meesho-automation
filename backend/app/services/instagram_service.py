import hmac
import hashlib
import logging
from typing import Optional, Dict, Any
import httpx
from app.core.config import settings
from app.core.security import decrypt_token, encrypt_token

logger = logging.getLogger("instagram_reseller")


def verify_webhook_signature(payload_bytes: bytes, x_hub_signature_header: Optional[str]) -> bool:
    """Verify Meta X-Hub-Signature-256 HMAC SHA-256 signature."""
    if not settings.INSTAGRAM_APP_SECRET:
        logger.warning("INSTAGRAM_APP_SECRET not configured, skipping signature verification in dev")
        return True
    if not x_hub_signature_header or not x_hub_signature_header.startswith("sha256="):
        return False
    
    expected_hash = x_hub_signature_header.split("sha256=")[1]
    mac = hmac.new(
        key=settings.INSTAGRAM_APP_SECRET.encode("utf-8"),
        msg=payload_bytes,
        digestmod=hashlib.sha256
    )
    calculated_hash = mac.hexdigest()
    return hmac.compare_digest(calculated_hash, expected_hash)


class MetaInstagramGraphService:
    """Official Meta Instagram Graph API Client."""
    BASE_URL = "https://graph.facebook.com/v19.0"

    @classmethod
    async def send_direct_message(
        cls,
        instagram_business_id: str,
        recipient_id: str,
        message_text: str,
        access_token: str
    ) -> Dict[str, Any]:
        """Send direct message to customer via official Meta Graph API."""
        url = f"{cls.BASE_URL}/{instagram_business_id}/messages"
        payload = {
            "recipient": {"id": recipient_id},
            "message": {"text": message_text}
        }
        headers = {"Authorization": f"Bearer {access_token}"}
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code != 200:
                logger.error(f"Meta Send DM failed ({response.status_code}): {response.text}")
                response.raise_for_status()
            return response.json()
