import json
from src.bot.intent import classify_intent
from src.bot.scripts import SCRIPTS
from src.services.whatsapp import send_message, send_buttons, send_list, send_flow
from src.db.queries import (
    get_seller_by_bot_number, get_seller_by_phone,
    get_conversation, create_conversation,
    update_conversation, get_products_by_seller,
    create_order, update_order, get_orders_by_seller,
)
from src.lib.redis_client import get_redis
from src.lib.config import get_settings

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

    # Global MENU
    if intent == "MENU":
        await update_conversation(conv["_id"], {
            "state": "idle", "cart": {}, "selected_product": None,
            "pending_order_id": None, "delivery_address": None,
        })
        _clear_cached_conv(seller_id, from_phone)
        conv = await get_conversation(seller_id, from_phone)
        if not conv:
            conv = await create_conversation(seller_id, f"whatsapp:{to_phone}", from_phone)
        _set_cached_conv(seller_id, from_phone, conv)
        return await handle_idle(seller, conv, from_phone)

    # Global TRACK
    if intent == "TRACK" and state not in ("delivery",):
        return await handle_track(seller, from_phone)

    # Global HANDOFF
    if intent == "HANDOFF":
        return await handle_handoff(seller, conv, from_phone)

    # State machine
    handlers = {
        "idle": handle_idle,
        "browse": handle_browse,
        "select": handle_select,
        "cart": handle_cart,
        "checkout": handle_checkout,
        "summary": handle_summary,
        "delivery": handle_delivery,
        "confirm": handle_confirm,
    }
    handler = handlers.get(state)
    if handler:
        if state == "idle":
            await handler(seller, conv, from_phone)
        elif state in ("browse", "select"):
            await handler(seller, conv, intent, text, from_phone)
        elif state == "cart":
            await handler(seller, conv, text, from_phone)
        elif state in ("checkout", "summary"):
            await handler(seller, conv, intent, from_phone)
        elif state == "delivery":
            await handler(seller, conv, text, from_phone)
        elif state == "confirm":
            await handler(seller, conv, intent, from_phone)


async def handle_flow_complete(from_phone: str, to_phone: str, screen: str, data: dict):
    """Handle response from WhatsApp Flow (payment confirmation)."""
    seller = await get_seller_by_bot_number(to_phone)
    if not seller:
        return

    seller_id = str(seller["_id"])
    conv = await _get_or_create_conv(seller_id, f"whatsapp:{to_phone}", from_phone)

    if screen == "PAYMENT_SCREEN":
        pending_id = conv.get("pending_order_id")
        if pending_id:
            from bson import ObjectId
            await update_order(ObjectId(pending_id), {"payment_status": "checking"})

        await send_message(from_phone, SCRIPTS["buyer"]["paid_checking"]())


async def _get_or_create_conv(seller_id, seller_wa: str, buyer_phone: str) -> dict:
    conv = _get_cached_conv(seller_id, buyer_phone)
    if conv:
        return conv
    conv = await get_conversation(seller_id, buyer_phone)
    if conv:
        _set_cached_conv(seller_id, buyer_phone, conv)
        return conv
    conv = await create_conversation(seller_id, seller_wa, buyer_phone)
    _set_cached_conv(seller_id, buyer_phone, conv)
    return conv


def _update_and_cache(conv: dict, seller_id: str, buyer_phone: str, updates: dict):
    import asyncio
    asyncio.create_task(update_conversation(conv["_id"], updates))
    conv.update(updates)
    conv["last_message_at"] = "now"
    _set_cached_conv(seller_id, buyer_phone, conv)


# ── BUYER STATE HANDLERS ─────────────────────────────────────────────────────

async def handle_idle(seller, conv, buyer):
    """Greet buyer warmly, then show products."""
    seller_id = str(seller["_id"])
    products = await get_products_by_seller(seller["_id"])
    if not products:
        _update_and_cache(conv, seller_id, buyer, {"state": "browse"})
        await send_message(buyer, SCRIPTS["buyer"]["shop_empty"](seller["shop_name"]))
        return

    greeting = SCRIPTS["buyer"]["welcome"](seller["shop_name"], seller.get("location", ""))
    await send_message(buyer, greeting)

    rows = []
    for i, p in enumerate(products):
        title = p["name"][:24]
        rows.append({
            "id": f"product_{i}",
            "title": title,
            "description": f"\u20a6{p['price_kobo']//100:,} | {p['stock_count']} in stock",
        })

    _update_and_cache(conv, seller_id, buyer, {"state": "browse"})
    await send_list(
        buyer,
        "Here's what we've got:",
        "Browse Products",
        [{"title": "Products", "rows": rows}],
    )


async def handle_browse(seller, conv, intent, text, buyer):
    seller_id = str(seller["_id"])

    if text.startswith("product_"):
        idx = int(text.split("_")[1])
    elif text.isdigit():
        idx = int(text) - 1
    else:
        products = await get_products_by_seller(seller["_id"])
        rows = [{"id": f"product_{i}", "title": p["name"][:24], "description": f"\u20a6{p['price_kobo']//100:,} | {p['stock_count']} in stock"} for i, p in enumerate(products)]
        await send_list(buyer, "Pick a product:", "Browse Products", [{"title": "Products", "rows": rows}])
        return

    products = await get_products_by_seller(seller["_id"])
    if idx < 0 or idx >= len(products):
        return await send_message(buyer, SCRIPTS["buyer"]["invalid"]())

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

    await send_buttons(
        buyer,
        SCRIPTS["buyer"]["product_detail"](product["name"], product["price_kobo"] // 100, product["stock_count"]),
        [
            {"id": "buy_now", "title": "Buy Now"},
            {"id": "ask_question", "title": "Ask Question"},
            {"id": "back_to_catalog", "title": "Back"},
        ],
    )


async def handle_select(seller, conv, intent, text, buyer):
    seller_id = str(seller["_id"])
    selected = conv.get("selected_product") or {}

    if intent == "CHECKOUT":
        _update_and_cache(conv, seller_id, buyer, {"state": "cart"})
        await send_message(buyer, SCRIPTS["buyer"]["qty_prompt"](selected.get("stock", 0)))
    elif intent == "QUESTION":
        _update_and_cache(conv, seller_id, buyer, {"handoff_active": True})
        await send_message(buyer, SCRIPTS["buyer"]["handoff"](seller["shop_name"]))
        await send_message(seller["phone_number"],
            f"\U0001F4AC Buyer *{buyer}* has a question about *{selected.get('name', 'a product')}*.\nReply to chat with them.")
    elif intent == "BROWSE":
        await handle_idle(seller, conv, buyer)
    else:
        await send_buttons(
            buyer,
            SCRIPTS["buyer"]["product_detail"](selected.get("name", ""), selected.get("price_kobo", 0) // 100, selected.get("stock", 0)),
            [
                {"id": "buy_now", "title": "Buy Now"},
                {"id": "ask_question", "title": "Ask Question"},
                {"id": "back_to_catalog", "title": "Back"},
            ],
        )


async def handle_cart(seller, conv, text, buyer):
    seller_id = str(seller["_id"])
    selected = conv.get("selected_product") or {}
    try:
        qty = int(text.strip())
    except ValueError:
        return await send_message(buyer, SCRIPTS["buyer"]["out_of_stock"](selected.get("stock", 0)))

    max_stock = selected.get("stock", 0)
    if qty < 1 or qty > max_stock:
        return await send_message(buyer, SCRIPTS["buyer"]["out_of_stock"](max_stock))

    price = selected.get("price_kobo", 0) // 100
    subtotal = qty * price
    _update_and_cache(conv, seller_id, buyer, {
        "state": "checkout",
        "cart": {"qty": qty, "price_kobo": selected.get("price_kobo", 0), "subtotal": subtotal},
    })

    await send_buttons(
        buyer,
        SCRIPTS["buyer"]["cart_summary"](qty, selected.get("name", ""), price, subtotal),
        [
            {"id": "confirm_order", "title": "Confirm"},
            {"id": "cancel_order", "title": "Cancel"},
        ],
    )


async def handle_checkout(seller, conv, intent, from_phone):
    seller_id = str(seller["_id"])
    if intent == "CONFIRM":
        settings = get_settings()
        flow_id = settings.CHECKOUT_FLOW_ID
        cart = conv.get("cart", {})
        selected = conv.get("selected_product") or {}
        total = cart.get("subtotal", 0)
        total_kobo = total * 100

        bank = seller.get("nomba_bank_name") or "Bank TBA"
        acct = seller.get("nomba_virtual_account") or "Account TBA"

        # Create order first
        order = await create_order(
            seller["_id"], from_phone,
            [{"product_id": selected.get("product_id"), "name": selected.get("name"),
              "qty": cart.get("qty", 0), "price_kobo": selected.get("price_kobo", 0)}],
            total_kobo, total_kobo, ""
        )

        _update_and_cache(conv, seller_id, from_phone, {
            "state": "confirm",
            "pending_order_id": str(order["_id"]),
        })

        if flow_id:
            await send_flow(
                from_phone,
                header_text="Complete Payment",
                body_text=f"Order: {selected.get('name', '')} x{cart.get('qty', 0)}\nTotal: \u20a6{total:,}",
                footer_text="Transfer and tap 'I've Transferred'",
                flow_id=flow_id,
                flow_token=f"checkout_{seller_id}_{from_phone}",
                flow_cta="Pay Now",
                flow_data={
                    "amount": f"\u20a6{total:,}",
                    "bank_name": bank,
                    "account_number": acct,
                    "account_name": seller.get("shop_name", ""),
                },
            )
        else:
            await send_message(from_phone, SCRIPTS["buyer"]["payment_details"](
                seller["shop_name"], bank, acct, total))
            await send_buttons(
                from_phone,
                "Transferred? Tap below:",
                [{"id": "paid", "title": "PAID"}, {"id": "cancel_order", "title": "Cancel"}],
            )
    elif intent == "CANCEL":
        _update_and_cache(conv, seller_id, from_phone, {
            "state": "idle", "cart": {}, "selected_product": None,
        })
        await send_message(from_phone, SCRIPTS["buyer"]["cancelled"]())
        await handle_idle(seller, conv, from_phone)
    else:
        cart = conv.get("cart", {})
        selected = conv.get("selected_product") or {}
        await send_buttons(
            from_phone,
            SCRIPTS["buyer"]["cart_summary"](cart.get("qty", 0), selected.get("name", ""), cart.get("price_kobo", 0) // 100, cart.get("subtotal", 0)),
            [
                {"id": "confirm_order", "title": "Confirm"},
                {"id": "cancel_order", "title": "Cancel"},
            ],
        )


async def handle_summary(seller, conv, intent, from_phone):
    await handle_checkout(seller, conv, intent, from_phone)


async def handle_delivery(seller, conv, text, buyer):
    """Fallback: buyer types address as plain text (when no Flow)."""
    seller_id = str(seller["_id"])
    cart = conv.get("cart", {})
    selected = conv.get("selected_product", {})
    qty = cart.get("qty", 0)
    price_kobo = cart.get("price_kobo", 0)
    total_kobo = qty * price_kobo

    order = await create_order(
        seller["_id"], buyer,
        [{"product_id": selected.get("product_id"), "name": selected.get("name"),
          "qty": qty, "price_kobo": price_kobo}],
        total_kobo, total_kobo, text
    )

    bank = seller.get("nomba_bank_name") or "Bank TBA"
    acct = seller.get("nomba_virtual_account") or "Account TBA"

    _update_and_cache(conv, seller_id, buyer, {
        "state": "confirm",
        "pending_order_id": str(order["_id"]),
        "delivery_address": text,
    })

    await send_message(buyer, SCRIPTS["buyer"]["payment_details"](
        seller["shop_name"], bank, acct, total_kobo // 100))

    await send_buttons(
        buyer,
        "Transferred? Tap below:",
        [{"id": "paid", "title": "PAID"}, {"id": "cancel_order", "title": "Cancel"}],
    )


async def handle_confirm(seller, conv, intent, from_phone):
    seller_id = str(seller["_id"])
    if intent == "PAID":
        pending_id = conv.get("pending_order_id")
        if pending_id:
            from bson import ObjectId
            await update_order(ObjectId(pending_id), {"payment_status": "checking"})
        await send_message(from_phone, SCRIPTS["buyer"]["paid_checking"]())

    elif intent == "CANCEL":
        pending_id = conv.get("pending_order_id")
        if pending_id:
            from bson import ObjectId
            await update_order(ObjectId(pending_id), {"status": "cancelled"})
        _update_and_cache(conv, seller_id, from_phone, {
            "state": "idle", "cart": {}, "selected_product": None,
        })
        await send_message(from_phone, SCRIPTS["buyer"]["cancelled"]())
        await handle_idle(seller, conv, from_phone)
    else:
        await send_buttons(
            from_phone,
            "Tap when ready:",
            [{"id": "paid", "title": "PAID"}, {"id": "cancel_order", "title": "Cancel"}],
        )


# ── NON-STATE HANDLERS ───────────────────────────────────────────────────────

async def handle_track(seller, buyer):
    orders = await get_orders_by_seller(seller["_id"], limit=3)
    if not orders:
        await send_message(buyer, SCRIPTS["buyer"]["track_none"]())
        return
    for order in orders:
        await send_message(buyer, SCRIPTS["buyer"]["track_status"](
            order["order_number"], order["status"]))


async def handle_handoff(seller, conv, buyer):
    seller_id = str(seller["_id"])
    _update_and_cache(conv, seller_id, buyer, {"handoff_active": True})
    await send_message(buyer, SCRIPTS["buyer"]["handoff"](seller["shop_name"]))
    await send_message(seller["phone_number"],
        f"\U0001F4E2 *Buyer needs help!*\nBuyer: {buyer}\nReply to chat. RESUME when done.")
