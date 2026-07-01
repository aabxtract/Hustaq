from src.bot.intent import classify_intent
from src.bot.scripts import SCRIPTS
from src.services.twilio import send_message
from src.db.queries import (
    get_seller_by_twilio_number, get_conversation, create_conversation,
    update_conversation, get_products_by_seller, get_product_by_id,
    create_order, update_order,
)

async def process_message(
    from_phone: str, to_phone: str,
    text: str, media_url: str | None
):
    seller = await get_seller_by_twilio_number(f"whatsapp:{to_phone}")
    if not seller:
        return
    if seller["bot_paused"]:
        return

    conv = await get_or_create_conv(seller["_id"], f"whatsapp:{to_phone}", from_phone)
    if conv["handoff_active"]:
        return

    intent = classify_intent(text, conv["state"])
    state = conv["state"]

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


async def get_or_create_conv(seller_id, seller_wa: str, buyer_phone: str) -> dict:
    conv = await get_conversation(seller_id, buyer_phone)
    if conv:
        return conv
    return await create_conversation(seller_id, seller_wa, buyer_phone)


async def handle_idle(seller, conv, intent, buyer):
    products = await get_products_by_seller(seller["_id"])
    catalog = SCRIPTS["buyer"]["BROWSE_catalog"](products)
    await update_conversation(conv["_id"], {"state": "browse"})
    await send_message(buyer, SCRIPTS["buyer"]["IDLE_greeting"](seller["shop_name"], catalog))


async def handle_browse(seller, conv, intent, text, buyer):
    if intent != "SELECT":
        return await send_message(buyer, SCRIPTS["buyer"]["INVALID_input"]())
    idx = int(text.strip()) - 1
    products = await get_products_by_seller(seller["_id"])
    if idx < 0 or idx >= len(products):
        return await send_message(buyer, SCRIPTS["buyer"]["INVALID_input"]())
    product = products[idx]
    await update_conversation(conv["_id"], {
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
    if intent == "CHECKOUT":
        await update_conversation(conv["_id"], {"state": "cart"})
        selected = conv.get("selected_product") or {}
        max_stock = selected.get("stock", 0)
        await send_message(buyer, SCRIPTS["buyer"]["CART_quantity"](max_stock))
    elif intent == "BROWSE":
        products = await get_products_by_seller(seller["_id"])
        catalog = SCRIPTS["buyer"]["BROWSE_catalog"](products)
        await update_conversation(conv["_id"], {"state": "browse"})
        await send_message(buyer, SCRIPTS["buyer"]["IDLE_greeting"](seller["shop_name"], catalog))
    else:
        await send_message(buyer, SCRIPTS["buyer"]["INVALID_input"]())


async def handle_cart(seller, conv, intent, text, buyer):
    selected = conv.get("selected_product") or {}
    qty = int(text.strip())
    max_stock = selected.get("stock", 0)
    if qty < 1 or qty > max_stock:
        return await send_message(buyer, SCRIPTS["buyer"]["OUT_OF_STOCK"](max_stock))
    price = selected.get("price_kobo", 0) // 100
    subtotal = qty * price
    await update_conversation(conv["_id"], {
        "state": "checkout",
        "cart": {"qty": qty, "price_kobo": selected.get("price_kobo", 0), "subtotal": subtotal},
    })
    await send_message(buyer, SCRIPTS["buyer"]["CART_summary"](qty, price, subtotal))


async def handle_checkout(seller, conv, intent, buyer):
    if intent == "CONFIRM":
        await update_conversation(conv["_id"], {"state": "delivery"})
        await send_message(buyer, SCRIPTS["buyer"]["CHECKOUT_address"]())
    elif intent == "CANCEL":
        await update_conversation(conv["_id"], {"state": "idle", "cart": {}, "selected_product": None})
        await send_message(buyer, SCRIPTS["buyer"]["CANCEL_order"]())
    else:
        await send_message(buyer, SCRIPTS["buyer"]["INVALID_input"]())


async def handle_delivery(seller, conv, text, buyer):
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

    await update_conversation(conv["_id"], {
        "state": "confirm",
        "pending_order_id": str(order["_id"]),
    })
    await send_message(buyer, SCRIPTS["buyer"]["CONFIRM_payment"](
        seller["shop_name"], bank, acct, total_kobo // 100))


async def handle_confirm(seller, conv, intent, buyer):
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
        await update_conversation(conv["_id"], {"state": "idle", "cart": {}, "selected_product": None})
        await send_message(buyer, SCRIPTS["buyer"]["CANCEL_order"]())
    else:
        await send_message(buyer, SCRIPTS["buyer"]["INVALID_input"]())
