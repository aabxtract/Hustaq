from fastapi import APIRouter, Request, Response
from src.lib.config import get_settings
from src.db.queries import (
    get_seller_by_twilio_number, get_seller_by_phone,
    update_conversation, get_conversation,
)
from src.services.state import process_message
from src.services.twilio import send_message, verify_twilio_signature
from src.bot.scripts import SCRIPTS

router = APIRouter()


# ── Meta webhook verification (GET) ───────────────────────────────────────────

@router.get("/twilio")
async def meta_webhook_verify(request: Request):
    """
    Meta sends a GET to verify the webhook.
    We must respond with the hub.challenge if hub.verify_token matches.
    """
    settings = get_settings()
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    print(f"[META VERIFY] mode={mode} token={token}")
    if mode == "subscribe" and token == settings.META_VERIFY_TOKEN:
        print("[META VERIFY] Webhook verified OK")
        return Response(content=challenge, status_code=200)
    print("[META VERIFY] Verification FAILED")
    return Response(status_code=403)


# ── Incoming WhatsApp messages (POST) ─────────────────────────────────────────

@router.post("/twilio")
async def whatsapp_webhook(request: Request):
    """
    Handles incoming WhatsApp messages from Meta Cloud API.
    Also handles legacy Twilio form-encoded format for backward compat.
    """
    settings = get_settings()
    content_type = request.headers.get("content-type", "")

    # ── Parse the incoming payload ─────────────────────────────────────────────
    if "application/x-www-form-urlencoded" in content_type:
        form = await request.form()
        params = dict(form)
        signature = request.headers.get("X-Twilio-Signature", "")
        url = str(request.url)
        if not verify_twilio_signature(settings.TWILIO_AUTH_TOKEN, signature, url, params):
            print("[WEBHOOK] Twilio signature FAILED")
            return Response(status_code=403)
        from_phone = params.get("From", "").replace("whatsapp:", "")
        to_phone = params.get("To", "").replace("whatsapp:", "")
        text = params.get("Body", "")
        media_url = params.get("MediaUrl0")
        print(f"[WEBHOOK] (Twilio format) From={from_phone} To={to_phone} Body={text}")
    else:
        raw = await request.json()
        changes = (raw.get("entry") or [{}])[0].get("changes") or [{}]
        value = changes[0].get("value", {})
        messages = value.get("messages")
        if not messages:
            return Response(content="", status_code=200)

        msg = messages[0]
        msg_type = msg.get("type", "text")
        from_phone = msg.get("from", "")
        metadata = value.get("metadata", {})
        to_phone = metadata.get("display_phone_number", "")
        if not to_phone.startswith("+"):
            to_phone = f"+{to_phone}"

        text, media_url = _extract_msg_content(msg, msg_type)

        print(f"[WEBHOOK] (Meta format) From={from_phone} To={to_phone} Body={text[:60]}")

    # ── Routing (same logic regardless of source format) ───────────────────────
    return await _route_message(from_phone, to_phone, text, media_url)


# ── Content extraction ────────────────────────────────────────────────────────

def _extract_msg_content(msg: dict, msg_type: str) -> tuple[str, str | None]:
    """Extract text and optional media URL from a Meta message object."""
    text = ""
    media_url = None
    if msg_type == "text":
        text = msg.get("text", {}).get("body", "")
    elif msg_type in ("image", "document", "video"):
        media_obj = msg.get(msg_type, {})
        media_url = media_obj.get("id", "")
        text = media_obj.get("caption", "")
    elif msg_type == "interactive":
        interactive = msg.get("interactive", {})
        if interactive.get("type") == "button_reply":
            text = interactive.get("button_reply", {}).get("title", "")
        elif interactive.get("type") == "list_reply":
            text = interactive.get("list_reply", {}).get("title", "")
    return text, media_url


# ── Routing logic (shared by both Meta and legacy Twilio formats) ─────────────

async def _route_message(from_phone: str, to_phone: str, text: str, media_url: str | None) -> Response:
    """Route an incoming message to the correct handler."""
    settings = get_settings()
    hustaq_number = settings.META_BOT_NUMBER.replace("whatsapp:", "")
    if not hustaq_number:
        hustaq_number = settings.TWILIO_WHATSAPP_NUMBER.replace("whatsapp:", "")

    # 1. Known seller texting Hustaq number → seller commands
    from_is_seller = await get_seller_by_phone(from_phone) is not None
    if to_phone == hustaq_number and from_is_seller:
        print("[WEBHOOK] -> seller command path")
        await _handle_seller_command(from_phone, text, media_url)
        return Response(content="", status_code=200)

    # 2. Unknown person texting Hustaq number → check seller keywords
    if to_phone == hustaq_number and not from_is_seller:
        seller_keywords = ("sell", "shop", "vendor", "register", "onboard", "join", "start")
        if any(k in text.lower() for k in seller_keywords):
            from src.services.seller_commands import handle_seller_command as _onboard
            print("[WEBHOOK] -> new seller onboarding path")
            await _onboard(from_phone, text, media_url)
            return Response(content="", status_code=200)

    # 3. Echo: seller texting their own shop's number → pause bot
    seller = await get_seller_by_twilio_number(to_phone)
    if seller and from_phone == seller["phone_number"]:
        print("[WEBHOOK] -> echo path")
        await _handle_echo(seller, from_phone)
        return Response(content="", status_code=200)

    # 4. Normal buyer message → state machine
    print("[WEBHOOK] -> buyer state machine path")
    await process_message(from_phone, to_phone, text, media_url)
    return Response(content="", status_code=200)


# ── Helper functions ──────────────────────────────────────────────────────────

async def _handle_seller_command(seller_phone: str, text: str, media_url: str | None):
    from src.services.seller_commands import handle_seller_command as _exec
    await _exec(seller_phone, text, media_url)


async def _handle_echo(seller: dict, seller_phone: str):
    conv = await get_conversation(seller["_id"], seller_phone)
    if conv:
        await update_conversation(conv["_id"], {"handoff_active": True})
    await send_message(seller_phone, SCRIPTS["seller"]["echo_pause"]("your buyer"))
