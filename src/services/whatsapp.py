"""
Meta WhatsApp Cloud API service.

Send text, buttons, lists, and flows via Meta's Graph API.
"""
import json
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


async def _send(payload: dict, label: str = "text") -> bool:
    print(f"[META SEND] {label}: {json.dumps(payload)[:120]}...")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(_graph_url(), json=payload, headers=_headers())
            data = resp.json()
            if resp.status_code in (200, 201):
                msg_id = data.get("messages", [{}])[0].get("id", "?")
                print(f"[META SEND] OK id={msg_id}")
                return True
            else:
                print(f"[META SEND] FAILED: {resp.status_code} {data}")
                return False
    except Exception as e:
        print(f"[META SEND] ERROR: {e}")
        return False


async def send_message(to: str, body: str) -> bool:
    to_clean = to.replace("whatsapp:", "")
    return await _send({
        "messaging_product": "whatsapp",
        "to": to_clean,
        "type": "text",
        "text": {"body": body},
    }, f"text to {to_clean}")


async def send_buttons(to: str, body: str, buttons: list[dict]) -> bool:
    to_clean = to.replace("whatsapp:", "")
    return await _send({
        "messaging_product": "whatsapp",
        "to": to_clean,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": body},
            "action": {"buttons": [
                {"type": "reply", "reply": {"id": b["id"], "title": b["title"]}}
                for b in buttons[:3]
            ]},
        },
    }, f"buttons to {to_clean}")


async def send_list(to: str, body: str, button_text: str, sections: list[dict]) -> bool:
    to_clean = to.replace("whatsapp:", "")
    return await _send({
        "messaging_product": "whatsapp",
        "to": to_clean,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": body},
            "action": {
                "button": button_text,
                "sections": sections,
            },
        },
    }, f"list to {to_clean}")


async def send_flow(
    to: str,
    header_text: str,
    body_text: str,
    footer_text: str,
    flow_id: str,
    flow_token: str,
    flow_cta: str,
    flow_action: str = "navigate",
    flow_action_payload: dict | None = None,
    flow_data: dict | None = None,
) -> bool:
    """Send a WhatsApp Flow message for in-app forms."""
    to_clean = to.replace("whatsapp:", "")
    params = {
        "flow_message_version": "3",
        "flow_token": flow_token,
        "flow_id": flow_id,
        "flow_cta": flow_cta,
        "flow_action": flow_action,
    }
    if flow_action_payload:
        params["flow_action_payload"] = flow_action_payload
    if flow_data:
        params["flow_action_payload"] = {
            "screen": "PAYMENT_SCREEN",
            "data": json.dumps(flow_data),
        }

    return await _send({
        "messaging_product": "whatsapp",
        "to": to_clean,
        "type": "interactive",
        "interactive": {
            "type": "flow",
            "header": {"type": "text", "text": header_text},
            "body": {"text": body_text},
            "footer": {"text": footer_text},
            "action": {
                "name": "flow",
                "parameters": params,
            },
        },
    }, f"flow to {to_clean}")
