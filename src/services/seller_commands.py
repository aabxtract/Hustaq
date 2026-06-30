import json
import os
from src.bot.scripts import SCRIPTS
from src.db import queries as db
from src.lib.redis_client import get_redis

CATEGORIES = {
    '1': 'Fashion', '2': 'Food and Drinks',
    '3': 'Beauty', '4': 'Gadgets', '5': 'Other',
}

ONBOARD_STEPS = ('WELCOME', 'SHOP_NAME', 'CATEGORY', 'LOCATION', 'DONE')


async def handle_seller_command(
    seller_phone: str,
    text: str,
    media_url: str | None,
    send_fn,
):
    seller = db.get_seller_by_phone(seller_phone)

    # Unknown number or bare new shop → check onboarding state first
    r = get_redis()
    onboard_key = f'onboard:{seller_phone}'
    onboard_step = r.get(onboard_key)

    if onboard_step:
        await _continue_onboarding(seller_phone, text, media_url, onboard_step, r, send_fn)
        return

    if not seller:
        await _start_onboarding(seller_phone, r, send_fn)
        return

    cmd = text.strip().lower()

    if cmd in ('menu', '0', 'start'):
        await send_fn(seller_phone, SCRIPTS['seller']['menu'](seller['shop_name']))

    elif cmd in ('1', 'add product'):
        await _prompt_product_photo(seller_phone, r, send_fn)

    elif cmd in ('2', 'view orders'):
        orders = db.get_seller_orders(str(seller['id']))
        await send_fn(seller_phone, SCRIPTS['seller']['order_list'](orders))

    elif cmd in ('3', 'check balance'):
        await send_fn(seller_phone, SCRIPTS['seller']['balance'](
            seller['balance_kobo'] // 100,
            seller['pending_balance_kobo'] // 100,
        ))

    elif cmd == 'pause':
        db.set_bot_paused(str(seller['id']), True)
        await send_fn(seller_phone, SCRIPTS['seller']['pause_confirmed']())

    elif cmd == 'resume':
        db.set_bot_paused(str(seller['id']), False)
        db.update_conv_handoff(str(seller['id']), False)
        await send_fn(seller_phone, SCRIPTS['seller']['resume_confirmed']())

    elif media_url:
        # Seller sent a photo — check if we're in product add flow
        prod_key = f'product_add:{seller_phone}'
        r.setex(prod_key, 1800, json.dumps({'photo_url': media_url, 'step': 'NAME'}))
        await send_fn(seller_phone, SCRIPTS['seller']['product_photo_received']())

    else:
        # Check if we're mid product-add flow
        prod_key = f'product_add:{seller_phone}'
        prod_state = r.get(prod_key)
        if prod_state:
            await _continue_product_add(seller, seller_phone, text, prod_state, r, send_fn)
        else:
            await send_fn(seller_phone, SCRIPTS['seller']['unknown'](seller['shop_name']))


# ---------------------------------------------------------------------------
# Onboarding
# ---------------------------------------------------------------------------

async def _start_onboarding(seller_phone: str, r, send_fn):
    db.upsert_seller_bare(seller_phone)
    r.setex(f'onboard:{seller_phone}', 3600, 'WELCOME')
    await send_fn(seller_phone, SCRIPTS['seller']['onboarding_welcome']())


async def _continue_onboarding(seller_phone, text, media_url, step, r, send_fn):
    key = f'onboard:{seller_phone}'
    t = text.strip()

    if step == 'WELCOME':
        if t.lower() in ('yes', 'y', 'ok', 'okay', 'sure', 'yeah'):
            r.setex(key, 3600, 'SHOP_NAME')
            await send_fn(seller_phone, SCRIPTS['seller']['onboarding_shopname']())
        else:
            await send_fn(seller_phone, SCRIPTS['seller']['onboarding_welcome']())

    elif step == 'SHOP_NAME':
        if len(t) < 2:
            await send_fn(seller_phone, SCRIPTS['seller']['onboarding_shopname']())
            return
        db.update_seller_shop_name(seller_phone, t)
        r.setex(key, 3600, 'CATEGORY')
        await send_fn(seller_phone, SCRIPTS['seller']['onboarding_category']())

    elif step == 'CATEGORY':
        category = CATEGORIES.get(t)
        if not category:
            await send_fn(seller_phone, SCRIPTS['seller']['onboarding_category']())
            return
        db.update_seller_category(seller_phone, category)
        r.setex(key, 3600, 'LOCATION')
        await send_fn(seller_phone, SCRIPTS['seller']['onboarding_location']())

    elif step == 'LOCATION':
        if len(t) < 3:
            await send_fn(seller_phone, SCRIPTS['seller']['onboarding_location']())
            return
        db.update_seller_location(seller_phone, t)

        # Link Hustaq's Twilio number so buyers reach this seller
        twilio_number = os.environ.get('TWILIO_WHATSAPP_NUMBER', '')
        db.update_seller_twilio_number(seller_phone, twilio_number)

        r.delete(key)
        seller = db.get_seller_by_phone(seller_phone)

        # Phase 2: create Nomba virtual account here
        # For now, complete onboarding without payment account
        await send_fn(seller_phone, SCRIPTS['seller']['onboarding_done'](seller['shop_name']))


# ---------------------------------------------------------------------------
# Product add flow
# ---------------------------------------------------------------------------

async def _prompt_product_photo(seller_phone, r, send_fn):
    await send_fn(seller_phone, 'Send a photo of your product to add it.')


async def _continue_product_add(seller, seller_phone, text, prod_state_raw, r, send_fn):
    prod_state = json.loads(prod_state_raw)
    prod_key = f'product_add:{seller_phone}'
    step = prod_state.get('step')

    if step == 'NAME':
        if len(text.strip()) < 2:
            await send_fn(seller_phone, SCRIPTS['seller']['product_photo_received']())
            return
        prod_state['name'] = text.strip()
        prod_state['step'] = 'PRICE'
        r.setex(prod_key, 1800, json.dumps(prod_state))
        await send_fn(seller_phone, SCRIPTS['seller']['product_name_received']())

    elif step == 'PRICE':
        cleaned = text.strip().replace(',', '').replace('₦', '').replace('N', '')
        if not cleaned.isdigit():
            await send_fn(seller_phone, SCRIPTS['seller']['invalid_price']())
            return
        price_naira = int(cleaned)
        price_kobo = price_naira * 100
        db.create_product(
            str(seller['id']),
            prod_state['name'],
            price_kobo,
            prod_state.get('photo_url', ''),
        )
        r.delete(prod_key)
        await send_fn(seller_phone, SCRIPTS['seller']['product_saved'](
            prod_state['name'], price_naira
        ))
