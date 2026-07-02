"""
Meta WhatsApp Cloud API service (replaces Twilio).

Send messages via Meta's Graph API.
"""
import httpx
from src.lib.config import get_settings

META_BASE = "https://graph.facebook.com"


def _headers():
    settings = get_settings()
    return {
        "Authorization": f"Bearer {settings.META_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }


def _graph_url():
    settings = get_settings()
    return f"{META_BASE}/{settings.META_API_VERSION}/{settings.META_PHONE_NUMBER_ID}/messages"


# ── Public API (same interface as before for backwards compat) ─────────────────

async def send_message(to: str, body: str) -> None:
    """Send a plain-text WhatsApp message via Meta Cloud API."""
    settings = get_settings()
    to_clean = to.replace("whatsapp:", "")
    payload = {
        "messaging_product": "whatsapp",
        "to": to_clean,
        "type": "text",
        "text": {"body": body},
    }
    print(f"[META SEND] to={to_clean} body={body[:80]}...")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(_graph_url(), json=payload, headers=_headers())
            data = resp.json()
            if resp.status_code in (200, 201):
                msg_id = data.get("messages", [{}])[0].get("id", "?")
                print(f"[META SEND] OK id={msg_id}")
            else:
                print(f"[META SEND] FAILED: {resp.status_code} {data}")
    except Exception as e:
        print(f"[META SEND] ERROR: {e}")


def verify_twilio_signature(auth_token: str, signature: str, url: str, params: dict) -> bool:
    """
    No-op for Meta. Meta does not use Twilio-style signature verification.
    Returns True so webhook processing continues.
    """
    return True

