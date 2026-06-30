import json
from src.bot.intent import classify_intent
from src.bot.scripts import SCRIPTS
from src.db import queries as db
from src.lib.redis_client import get_redis


# Key helpers — all state stored in Redis, DB only for durable records

def _sel_key(conv_id: str) -> str:
    return f'conv:select:{conv_id}'


def _cart_key(conv_id: str) -> str:
    return f'conv:cart:{conv_id}'


async def process_message(
    from_phone: str,
    to_phone: str,
    text: str,
    media_url: str | None,
    send_fn,          # injected to avoid circular import: async def send_fn(to, body)
):
    from src.db.queries import get_seller_by_twilio_number, get_all_active_sellers

    twilio_wa = f'whatsapp:{to_phone}'
    seller = get_seller_by_twilio_number(twilio_wa)

    # One-number-for-all: if no seller matched this specific twilio_number,
    # look up the buyer's existing conversation to find their seller,
    # or route to a directory of all active sellers.
    conv = None
    if not seller:
        sellers = get_all_active_sellers()
        if not sellers:
            return
        if len(sellers) == 1:
            seller = sellers[0]
        else:
            # Check if buyer already has an active conversation
            for s in sellers:
                existing = db.get_conversation(twilio_wa, from_phone)
                if existing:
                    seller = db.get_seller_by_phone(s['phone_number'])
                    if seller and str(seller['id']) == str(existing['seller_id']):
                        conv = existing
                        break
            if not seller:
                await _show_directory(from_phone, twilio_wa, sellers, send_fn)
                return

    if seller['bot_paused']:
        return

    if conv is None:
        conv = db.get_conversation(twilio_wa, from_phone)
    if conv is None:
        conv = db.create_conversation(str(seller['id']), twilio_wa, from_phone)
    if conv['handoff_active']:
        return

    state = conv['state']
    intent = classify_intent(text, state)

    # Global MENU reset from any state
    if intent == 'MENU':
        db.reset_conversation(conv['id'])
        conv = db.get_conversation(twilio_wa, from_phone)
        return await handle_idle(seller, conv, from_phone, send_fn)

    if state == 'idle':
        await handle_idle(seller, conv, from_phone, send_fn)
    elif state == 'directory':
        await handle_directory(seller, conv, intent, text, from_phone, twilio_wa, send_fn)
    elif state == 'browse':
        await handle_browse(seller, conv, intent, text, from_phone, send_fn)
    elif state == 'select':
        await handle_select(seller, conv, intent, text, from_phone, send_fn)
    elif state == 'cart':
        await handle_cart(seller, conv, intent, text, from_phone, send_fn)
    elif state == 'checkout':
        await handle_checkout(seller, conv, intent, from_phone, send_fn)
    elif state == 'delivery':
        await handle_delivery(seller, conv, text, from_phone, send_fn)
    elif state == 'confirm':
        await handle_confirm(seller, conv, intent, from_phone, send_fn)


# ---------------------------------------------------------------------------
# Directory — shown when there are multiple sellers and buyer is new
# ---------------------------------------------------------------------------

async def _show_directory(buyer: str, twilio_wa: str, sellers: list, send_fn):
    r = get_redis()
    r.setex(f'directory:{buyer}', 1800, json.dumps([
        {'id': str(s['id']), 'shop_name': s['shop_name'],
         'category': s['category'], 'location': s['location']}
        for s in sellers
    ]))
    await send_fn(buyer, SCRIPTS['buyer']['welcome_directory'](sellers))


async def handle_directory(seller, conv, intent, text, buyer, twilio_wa, send_fn):
    r = get_redis()
    raw = r.get(f'directory:{buyer}')
    if not raw or not text.strip().isdigit():
        await send_fn(buyer, SCRIPTS['buyer']['INVALID_input']())
        return
    sellers_list = json.loads(raw)
    idx = int(text.strip()) - 1
    if idx < 0 or idx >= len(sellers_list):
        await send_fn(buyer, SCRIPTS['buyer']['INVALID_input']())
        return
    chosen = sellers_list[idx]
    conv = db.create_conversation(chosen['id'], twilio_wa, buyer)
    seller = db.get_seller_by_phone(chosen['id'])
    # Refresh with actual seller object from DB
    from src.db.queries import get_seller_by_twilio_number
    # seller_id lookup
    rows = db.query('SELECT * FROM sellers WHERE id = %s', (chosen['id'],)) if hasattr(db, 'query') else []
    from src.lib.db import query
    sellers_row = query('SELECT * FROM sellers WHERE id = %s', (chosen['id'],))
    if sellers_row:
        seller = sellers_row[0]
        await handle_idle(seller, conv, buyer, send_fn)


# ---------------------------------------------------------------------------
# State handlers
# ---------------------------------------------------------------------------

async def handle_idle(seller, conv, buyer, send_fn):
    products = db.get_products(str(seller['id']))
    catalog = SCRIPTS['buyer']['BROWSE_catalog'](products)
    db.update_conv_state(conv['id'], 'browse')
    await send_fn(buyer, SCRIPTS['buyer']['IDLE_greeting'](seller['shop_name'], catalog))


async def handle_browse(seller, conv, intent, text, buyer, send_fn):
    if intent != 'SELECT':
        products = db.get_products(str(seller['id']))
        catalog = SCRIPTS['buyer']['BROWSE_catalog'](products)
        await send_fn(buyer, SCRIPTS['buyer']['MENU'](seller['shop_name'], catalog))
        return

    products = db.get_products(str(seller['id']))
    idx = int(text.strip()) - 1
    if idx < 0 or idx >= len(products):
        await send_fn(buyer, SCRIPTS['buyer']['INVALID_input']())
        return

    product = products[idx]
    if product['stock_count'] <= 0:
        await send_fn(buyer, SCRIPTS['buyer']['NO_STOCK']())
        return

    r = get_redis()
    r.setex(_sel_key(conv['id']), 3600, json.dumps({
        'product_id': str(product['id']),
        'name': product['name'],
        'price_kobo': product['price_kobo'],
        'stock': product['stock_count'],
    }))
    db.update_conv_state(conv['id'], 'select')
    await send_fn(buyer, SCRIPTS['buyer']['SELECT_product'](
        product['name'], product['price_kobo'] // 100, product['stock_count']
    ))


async def handle_select(seller, conv, intent, text, buyer, send_fn):
    if intent == 'CANCEL' or text.strip() == '3':
        # Back to catalog
        db.update_conv_state(conv['id'], 'browse')
        products = db.get_products(str(seller['id']))
        catalog = SCRIPTS['buyer']['BROWSE_catalog'](products)
        await send_fn(buyer, SCRIPTS['buyer']['MENU'](seller['shop_name'], catalog))
        return

    if intent == 'HANDOFF' or text.strip() == '2':
        db.update_conv_handoff(str(seller['id']), True)
        await send_fn(buyer, SCRIPTS['buyer']['HANDOFF_notify'](seller['shop_name']))
        return

    # '1' or any CHECKOUT intent → ask quantity
    if intent not in ('CHECKOUT', 'SELECT') and text.strip() != '1':
        await send_fn(buyer, SCRIPTS['buyer']['INVALID_input']())
        return

    r = get_redis()
    sel_raw = r.get(_sel_key(conv['id']))
    if not sel_raw:
        db.update_conv_state(conv['id'], 'idle')
        return await handle_idle(seller, conv, buyer, send_fn)

    sel = json.loads(sel_raw)
    db.update_conv_state(conv['id'], 'cart')
    await send_fn(buyer, SCRIPTS['buyer']['CART_quantity'](sel['stock']))


async def handle_cart(seller, conv, intent, text, buyer, send_fn):
    r = get_redis()
    sel_raw = r.get(_sel_key(conv['id']))
    if not sel_raw:
        db.update_conv_state(conv['id'], 'idle')
        return await handle_idle(seller, conv, buyer, send_fn)

    sel = json.loads(sel_raw)

    if not text.strip().isdigit():
        await send_fn(buyer, SCRIPTS['buyer']['CART_quantity'](sel['stock']))
        return

    qty = int(text.strip())
    if qty <= 0:
        await send_fn(buyer, SCRIPTS['buyer']['CART_quantity'](sel['stock']))
        return
    if qty > sel['stock']:
        await send_fn(buyer, SCRIPTS['buyer']['OUT_OF_STOCK'](sel['stock']))
        return

    price = sel['price_kobo']
    subtotal = price * qty
    cart = [{'product_id': sel['product_id'], 'name': sel['name'],
              'price_kobo': price, 'qty': qty}]
    r.setex(_cart_key(conv['id']), 3600, json.dumps(cart))
    db.update_conv_state(conv['id'], 'checkout')
    await send_fn(buyer, SCRIPTS['buyer']['CART_summary'](
        qty, price // 100, subtotal // 100
    ))


async def handle_checkout(seller, conv, intent, buyer, send_fn):
    if intent == 'CANCEL':
        db.reset_conversation(conv['id'])
        await send_fn(buyer, SCRIPTS['buyer']['CANCEL_order']())
        return

    if intent != 'CONFIRM':
        await send_fn(buyer, SCRIPTS['buyer']['INVALID_input']())
        return

    db.update_conv_state(conv['id'], 'delivery')
    await send_fn(buyer, SCRIPTS['buyer']['CHECKOUT_address']())


async def handle_delivery(seller, conv, text, buyer, send_fn):
    r = get_redis()
    cart_raw = r.get(_cart_key(conv['id']))
    if not cart_raw:
        db.reset_conversation(conv['id'])
        return await handle_idle(seller, conv, buyer, send_fn)

    address = text.strip()
    if len(address) < 5:
        await send_fn(buyer, SCRIPTS['buyer']['CHECKOUT_address']())
        return

    cart = json.loads(cart_raw)
    subtotal_kobo = sum(item['price_kobo'] * item['qty'] for item in cart)
    total_kobo = subtotal_kobo  # no fees in Phase 1

    order = db.create_order(
        str(seller['id']), buyer, cart, subtotal_kobo, total_kobo, address
    )
    db.update_conv_state(conv['id'], 'confirm')
    db.set_pending_order(conv['id'], str(order['id']))

    # Decrement stock
    for item in cart:
        db.decrement_stock(item['product_id'], item['qty'])

    # Use real Nomba details if available, else static placeholder
    bank = seller.get('nomba_bank_name') or 'First Bank'
    acct = seller.get('nomba_virtual_account') or '0123456789 (demo)'

    await send_fn(buyer, SCRIPTS['buyer']['CONFIRM_payment'](
        seller['shop_name'], bank, acct, total_kobo // 100
    ))


async def handle_confirm(seller, conv, intent, buyer, send_fn):
    if intent == 'CANCEL':
        db.reset_conversation(conv['id'])
        await send_fn(buyer, SCRIPTS['buyer']['CANCEL_order']())
        return

    if intent != 'PAID':
        await send_fn(buyer, SCRIPTS['buyer']['CONFIRM_checking']())
        return

    # Phase 1: acknowledge manually — Phase 2 Nomba webhook does the real confirm
    await send_fn(buyer, SCRIPTS['buyer']['CONFIRM_checking']())
