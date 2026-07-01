import os
from fastapi import APIRouter, Request, Response
from src.lib.secrets import get_secret
from src.lib.redis_client import get_redis
from src.db import queries as db
from src.bot.scripts import SCRIPTS
from src.services.twilio_svc import send_message, verify_twilio_signature
from src.services.state import process_message
from src.services.seller_commands import handle_seller_command

router = APIRouter()


@router.post('/twilio')
async def twilio_webhook(request: Request):
    form = await request.form()
    params = dict(form)

    # Verify Twilio signature (skip locally via env var)
    if os.environ.get('SKIP_TWILIO_VERIFY', '').lower() != 'true':
        auth_token = get_secret('hustaq/twilio/auth_token')
        signature = request.headers.get('X-Twilio-Signature', '')
        url = str(request.url)
        if not verify_twilio_signature(auth_token, signature, url, params):
            return Response(status_code=403)

    from_phone = params.get('From', '').replace('whatsapp:', '')
    to_phone = params.get('To', '').replace('whatsapp:', '')
    text = params.get('Body', '').strip()
    media_url = params.get('MediaUrl0')
    num_media = int(params.get('NumMedia', '0'))

    hustaq_number = os.environ.get('TWILIO_WHATSAPP_NUMBER', '').replace('whatsapp:', '')

    # Check if sender is a known seller or mid-onboarding
    from_is_seller = db.get_seller_by_phone(from_phone) is not None
    from src.lib.redis_client import get_redis as _get_redis
    _r = _get_redis()
    from_is_onboarding = _r.get(f'onboard:{from_phone}') is not None

    # Single-number routing:
    # - Known sellers (or onboarding) texting Hustaq number → seller commands
    # - Everyone else texting Hustaq number → buyer state machine
    if to_phone == hustaq_number and (from_is_seller or from_is_onboarding):
        resolved_media = None
        if num_media > 0 and media_url:
            seller = db.get_seller_by_phone(from_phone)
            if seller:
                from src.services.twilio_svc import save_media_to_s3
                resolved_media = await save_media_to_s3(media_url, str(seller['id']))
            else:
                resolved_media = media_url
        await handle_seller_command(from_phone, text, resolved_media, send_message)
        return Response(content='', status_code=200)

    # New unknown number texting Hustaq number for first time → start seller onboarding
    # (handles "I want to sell" style messages)
    if to_phone == hustaq_number and not from_is_seller and not from_is_onboarding:
        # Check if message looks like seller intent keywords
        seller_keywords = ('sell', 'shop', 'vendor', 'register', 'onboard', 'join', 'start')
        if any(k in text.lower() for k in seller_keywords):
            await handle_seller_command(from_phone, text, None, send_message)
            return Response(content='', status_code=200)

    # Echo detection: seller texting from personal phone to buyer's conversation number
    seller = db.get_seller_by_twilio_number(f'whatsapp:{to_phone}')
    if seller and from_phone == seller['phone_number']:
        await _handle_echo(seller, from_phone)
        return Response(content='', status_code=200)

    # Buyer message → state machine
    await process_message(from_phone, to_phone, text, media_url, send_message)
    return Response(content='', status_code=200)


async def _handle_echo(seller: dict, seller_phone: str):
    r = get_redis()
    db.update_conv_handoff(str(seller['id']), True)
    alerted_key = f'echo:alerted:{seller["id"]}'
    if not r.get(alerted_key):
        await send_message(seller_phone, SCRIPTS['seller']['echo_pause']('your buyer'))
        r.setex(alerted_key, 1800, '1')
