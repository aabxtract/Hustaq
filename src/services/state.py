import json
from src.bot.intent import classify_intent
from src.bot.scripts import SCRIPTS
from src.services.whatsapp import send_message
from src.db.queries import (
    get_seller_by_bot_number, get_conversation, create_conversation,
    update_conversation, get_products_by_seller,
    create_order, update_order,
)
from src.lib.redis_client import get_redis

# Redis TTL for conversation cache (1 hour)
CONV_TTL = 3600


def _conv_cache_key(seller_id, buyer_phone: str) -> str:
    return f"conv:{seller_id}:{buyer_phone}"


def _get_cached_conv(seller_id, buyer_phone: str) -> dict | None:
    r = get_redis()
    raw = r.get(_conv_cache_key(seller_id, buyer_phone))
    return json.loads(raw) if raw else None


def _set_cached_conv(seller_id, buyer_phone: str, conv: dict):
    r = get_redis()
    r.setex(_conv_cache_key(seller_id, buyer_phone), CONV_TTL, json.dumps(conv, default=str))


def _clear_cached_conv(seller_id, buyer_phone: str):
    r = get_redis()
    r.delete(_conv_cache_key(seller_id, buyer_phone))


async def process_message(
    from_phone: str, to_phone: str,
    text: str, media_url: str | None
):
    seller = await get_seller_by_bot_number(to_phone)
    if not seller:
        print(f"[STATE] No seller found for bot_number='{to_phone}'")
        return
    if seller["bot_paused"]:
        print("[STATE] Bot is paused for this seller")
        return

    seller_id = str(seller["_id"])
    conv = await _get_or_create_conv(seller_id, f"whatsapp:{to_phone}", from_phone)
    if conv["handoff_active"]:
        print("[STATE] Handoff active, skipping")
        return

    intent = classify_intent(text, conv["state"])
    state = conv["state"]
    print(f"[STATE] seller={seller['shop_name']} state={state} intent={intent} text={text}")

    # Global MENU reset from any state
    if intent == "MENU":
        await update_conversation(conv["_id"], {
            "state": "idle", "cart": {}, "selected_product": None, "pending_order_id": None,
        })
        _clear_cached_conv(seller_id, from_phone)
        conv = await get_conversation(seller_id, from_phone)
        if not conv:
            conv = await create_conversation(seller_id, f"whatsapp:{to_phone}", from_phone)
        _set_cached_conv(seller_id, from_phone, conv)
        return await handle_idle(seller, conv, intent, from_phone)

    if state == "idle":
        await handle_idle(seller, conv, intent, from_phone)
    elif state == "browse":
        await handle_browse(seller, conv, intent, text, from_phone)
    elif state == "select":
        await handle_select(seller, conv, intent, text, from_phone)
    elif state == "cart":
        await handle_cart(seller, conv, intent, text, from_phone)
    elif state == "checkout":
        await handle_checkout(seller, conv, intent, from_phone)
    elif state == "delivery":
        await handle_delivery(seller, conv, text, from_phone)
    elif state == "confirm":
        await handle_confirm(seller, conv, intent, from_phone)


async def _get_or_create_conv(seller_id, seller_wa: str, buyer_phone: str) -> dict:
    # Try Redis cache first
    conv = _get_cached_conv(seller_id, buyer_phone)
    if conv:
        return conv

    # Cache miss — fetch from MongoDB
    conv = await get_conversation(seller_id, buyer_phone)
    if conv:
        _set_cached_conv(seller_id, buyer_phone, conv)
        return conv

    # New conversation
    conv = await create_conversation(seller_id, seller_wa, buyer_phone)
    _set_cached_conv(seller_id, buyer_phone, conv)
    return conv


def _update_and_cache(conv: dict, seller_id: str, buyer_phone: str, updates: dict):
    """Update MongoDB and refresh Redis cache in one shot."""
    import asyncio
    asyncio.create_task(update_conversation(conv["_id"], updates))
    conv.update(updates)
    conv["last_message_at"] = "now"
    _set_cached_conv(seller_id, buyer_phone, conv)


async def handle_idle(seller, conv, intent, buyer):
    seller_id = str(seller["_id"])
    products = await get_products_by_seller(seller["_id"])
    catalog = SCRIPTS["buyer"]["BROWSE_catalog"](products)
    _update_and_cache(conv, seller_id, buyer, {"state": "browse"})
    await send_message(buyer, SCRIPTS["buyer"]["IDLE_greeting"](seller["shop_name"], catalog))


async def handle_browse(seller, conv, intent, text, buyer):
    seller_id = str(seller["_id"])
    if intent != "SELECT":
        products = await get_products_by_seller(seller["_id"])
        catalog = SCRIPTS["buyer"]["BROWSE_catalog"](products)
        await send_message(buyer, f'{seller["shop_name"]} - Products:\n\n{catalog}\n\nReply a number to order.')
        return
    idx = int(text.strip()) - 1
    products = await get_products_by_seller(seller["_id"])
    if idx < 0 or idx >= len(products):
        return await send_message(buyer, SCRIPTS["buyer"]["INVALID_input"]())
    product = products[idx]
    _update_and_cache(conv, seller_id, buyer, {
        "state": "select",
        "selected_product": {
            "product_id": str(product["_id"]),
            "name": product["name"],
            "price_kobo": product["price_kobo"],
            "stock": product["stock_count"],
        },
    })
    await send_message(buyer, SCRIPTS["buyer"]["SELECT_product"](
        product["name"], product["price_kobo"] // 100, product["stock_count"]))


async def handle_select(seller, conv, intent, text, buyer):
    seller_id = str(seller["_id"])
    if intent == "CHECKOUT":
        _update_and_cache(conv, seller_id, buyer, {"state": "cart"})
        selected = conv.get("selected_product") or {}
        max_stock = selected.get("stock", 0)
        await send_message(buyer, SCRIPTS["buyer"]["CART_quantity"](max_stock))
    elif intent == "BROWSE":
        products = await get_products_by_seller(seller["_id"])
        catalog = SCRIPTS["buyer"]["BROWSE_catalog"](products)
        _update_and_cache(conv, seller_id, buyer, {"state": "browse"})
        await send_message(buyer, SCRIPTS["buyer"]["IDLE_greeting"](seller["shop_name"], catalog))
    else:
        await send_message(buyer, SCRIPTS["buyer"]["INVALID_input"]())


async def handle_cart(seller, conv, intent, text, buyer):
    seller_id = str(seller["_id"])
    selected = conv.get("selected_product") or {}
    qty = int(text.strip())
    max_stock = selected.get("stock", 0)
    if qty < 1 or qty > max_stock:
        return await send_message(buyer, SCRIPTS["buyer"]["OUT_OF_STOCK"](max_stock))
    price = selected.get("price_kobo", 0) // 100
    subtotal = qty * price
    _update_and_cache(conv, seller_id, buyer, {
        "state": "checkout",
        "cart": {"qty": qty, "price_kobo": selected.get("price_kobo", 0), "subtotal": subtotal},
    })
    await send_message(buyer, SCRIPTS["buyer"]["CART_summary"](qty, price, subtotal))


async def handle_checkout(seller, conv, intent, buyer):
    seller_id = str(seller["_id"])
    if intent == "CONFIRM":
        _update_and_cache(conv, seller_id, buyer, {"state": "delivery"})
        await send_message(buyer, SCRIPTS["buyer"]["CHECKOUT_address"]())
    elif intent == "CANCEL":
        _update_and_cache(conv, seller_id, buyer, {"state": "idle", "cart": {}, "selected_product": None})
        await send_message(buyer, SCRIPTS["buyer"]["CANCEL_order"]())
    else:
        await send_message(buyer, SCRIPTS["buyer"]["INVALID_input"]())


async def handle_delivery(seller, conv, text, buyer):
    seller_id = str(seller["_id"])
    cart = conv.get("cart", {})
    selected = conv.get("selected_product", {})

    items = [{
        "product_id": selected.get("product_id"),
        "name": selected.get("name"),
        "qty": cart.get("qty", 0),
        "price_kobo": cart.get("price_kobo", 0),
    }]
    total_kobo = cart.get("qty", 0) * cart.get("price_kobo", 0)

    order = await create_order(
        seller["_id"], buyer, items, total_kobo, total_kobo, text
    )

    bank = seller.get("nomba_bank_name") or "Bank TBA"
    acct = seller.get("nomba_virtual_account") or "Account TBA"

    _update_and_cache(conv, seller_id, buyer, {
        "state": "confirm",
        "pending_order_id": str(order["_id"]),
    })
    await send_message(buyer, SCRIPTS["buyer"]["CONFIRM_payment"](
        seller["shop_name"], bank, acct, total_kobo // 100))


async def handle_confirm(seller, conv, intent, buyer):
    seller_id = str(seller["_id"])
    if intent == "PAID":
        pending_id = conv.get("pending_order_id")
        if pending_id:
            from bson import ObjectId
            await update_order(ObjectId(pending_id), {"payment_status": "checking"})
        await send_message(buyer, SCRIPTS["buyer"]["CONFIRM_checking"]())
    elif intent == "CANCEL":
        pending_id = conv.get("pending_order_id")
        if pending_id:
            from bson import ObjectId
            await update_order(ObjectId(pending_id), {"status": "cancelled"})
        _update_and_cache(conv, seller_id, buyer, {"state": "idle", "cart": {}, "selected_product": None})
        await send_message(buyer, SCRIPTS["buyer"]["CANCEL_order"]())
    else:
        await send_message(buyer, SCRIPTS["buyer"]["INVALID_input"]())
