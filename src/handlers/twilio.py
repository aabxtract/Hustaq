from fastapi import APIRouter, Request, Response
from src.lib.config import settings
from src.db.queries import get_seller_by_twilio_number
from src.services.state import process_message
from src.services.twilio import send_message, verify_twilio_signature
from src.bot.scripts import SCRIPTS

router = APIRouter()

@router.post("/twilio")
async def twilio_webhook(request: Request):
    # 1. Parse form-encoded body (Twilio sends application/x-www-form-urlencoded)
    form = await request.form()
    params = dict(form)

    # 2. Verify Twilio signature
    signature = request.headers.get("X-Twilio-Signature", "")
    url = str(request.url)
    if not verify_twilio_signature(settings.TWILIO_AUTH_TOKEN, signature, url, params):
        return Response(status_code=403)

    # 3. Extract fields
    from_phone = params["From"].replace("whatsapp:", "")
    to_phone = params["To"].replace("whatsapp:", "")
    text = params.get("Body", "")
    media_url = params.get("MediaUrl0")

    # 4. Echo detection — seller chatting manually from their own phone
    seller = await get_seller_by_twilio_number(f"whatsapp:{to_phone}")
    if seller and from_phone == seller["phone_number"]:
        from src.handlers.twilio import handle_echo
        await handle_echo(seller, from_phone)
        return Response(content="", status_code=200)

    # 5. Route seller bot commands (message TO Hustaq central number)
    hustaq_number = settings.TWILIO_WHATSAPP_NUMBER.replace("whatsapp:", "")
    if to_phone == hustaq_number:
        from src.services.seller_commands import handle_seller_command
        await handle_seller_command(from_phone, text, media_url)
        return Response(content="", status_code=200)

    # 6. Normal buyer message — run through state machine
    await process_message(from_phone, to_phone, text, media_url)
    return Response(content="", status_code=200)


async def handle_echo(seller: dict, seller_phone: str):
    from src.db.queries import update_conversation, get_conversation
    conv = await get_conversation(seller["_id"], seller_phone)
    if conv:
        await update_conversation(conv["_id"], {"handoff_active": True})
    await send_message(seller_phone, SCRIPTS["seller"]["echo_pause"]("your buyer"))
