import json
from src.db.queries import (
    get_seller_by_phone, create_seller, update_seller,
    get_orders_by_seller, create_product,
)
from src.bot.scripts import SCRIPTS
from src.services.twilio import send_message
from src.lib.redis_client import get_redis

CATEGORIES = {
    "1": "Fashion", "2": "Food and Drinks",
    "3": "Beauty", "4": "Gadgets", "5": "Other",
}


async def handle_seller_command(seller_phone: str, text: str, media_url: str | None):
    seller = await get_seller_by_phone(seller_phone)
    r = get_redis()
    onboard_key = f"onboard:{seller_phone}"
    onboard_step = r.get(onboard_key)

    if onboard_step:
        await _continue_onboarding(seller_phone, text, media_url, onboard_step, r, send_message)
        return

    if not seller:
        await _start_onboarding(seller_phone, r, send_message)
        return

    cmd = text.strip().lower()

    if cmd in ("menu", "0", "start"):
        await send_message(seller_phone, SCRIPTS["seller"]["menu"](seller["shop_name"]))
    elif cmd in ("1", "add product"):
        await send_message(seller_phone, "Send a photo of your product to add it.")
    elif cmd in ("2", "view orders"):
        orders = await get_orders_by_seller(seller["_id"])
        await send_message(seller_phone, SCRIPTS["seller"]["order_list"](orders))
    elif cmd in ("3", "check balance"):
        await send_message(seller_phone, SCRIPTS["seller"]["balance"](
            seller["balance_kobo"] // 100,
            seller["pending_balance_kobo"] // 100,
        ))
    elif cmd == "pause":
        await update_seller(seller["_id"], {"bot_paused": True})
        await send_message(seller_phone, SCRIPTS["seller"]["pause_confirmed"]())
    elif cmd == "resume":
        await update_seller(seller["_id"], {"bot_paused": False})
        await send_message(seller_phone, SCRIPTS["seller"]["resume_confirmed"]())
    elif media_url:
        prod_key = f"product_add:{seller_phone}"
        r.setex(prod_key, 1800, json.dumps({"photo_url": media_url, "step": "NAME"}))
        await send_message(seller_phone, SCRIPTS["seller"]["product_photo_received"]())
    else:
        prod_key = f"product_add:{seller_phone}"
        prod_state = r.get(prod_key)
        if prod_state:
            await _continue_product_add(seller, seller_phone, text, prod_state, r, send_message)
        else:
            await send_message(seller_phone, SCRIPTS["seller"]["unknown"](seller["shop_name"]))


async def _start_onboarding(seller_phone: str, r, send_fn):
    seller = await create_seller(seller_phone, "New Shop", f"shop-{seller_phone[-4:]}")
    r.setex(f"onboard:{seller_phone}", 3600, "WELCOME")
    await send_fn(seller_phone, SCRIPTS["seller"]["onboarding_welcome"]())


async def _continue_onboarding(seller_phone, text, media_url, step, r, send_fn):
    key = f"onboard:{seller_phone}"
    t = text.strip()

    if step == "WELCOME":
        if t.lower() in ("yes", "y", "ok", "okay", "sure", "yeah"):
            r.setex(key, 3600, "SHOP_NAME")
            await send_fn(seller_phone, SCRIPTS["seller"]["onboarding_shopname"]())
        else:
            await send_fn(seller_phone, SCRIPTS["seller"]["onboarding_welcome"]())

    elif step == "SHOP_NAME":
        if len(t) < 2:
            await send_fn(seller_phone, SCRIPTS["seller"]["onboarding_shopname"]())
            return
        seller = await get_seller_by_phone(seller_phone)
        slug = t.lower().replace(" ", "-")
        await update_seller(seller["_id"], {"shop_name": t, "shop_slug": slug})
        r.setex(key, 3600, "CATEGORY")
        await send_fn(seller_phone, SCRIPTS["seller"]["onboarding_category"]())

    elif step == "CATEGORY":
        category = CATEGORIES.get(t)
        if not category:
            await send_fn(seller_phone, SCRIPTS["seller"]["onboarding_category"]())
            return
        seller = await get_seller_by_phone(seller_phone)
        await update_seller(seller["_id"], {"category": category})
        r.setex(key, 3600, "LOCATION")
        await send_fn(seller_phone, SCRIPTS["seller"]["onboarding_location"]())

    elif step == "LOCATION":
        if len(t) < 3:
            await send_fn(seller_phone, SCRIPTS["seller"]["onboarding_location"]())
            return
        seller = await get_seller_by_phone(seller_phone)
        await update_seller(seller["_id"], {"location": t})
        r.delete(key)

        from src.services.nomba import create_virtual_account
        try:
            acct = await create_virtual_account(str(seller["_id"]), seller["shop_name"])
            await update_seller(seller["_id"], {
                "nomba_virtual_account": acct["account_number"],
                "nomba_bank_name": acct["bank_name"],
                "nomba_bank_code": acct["bank_code"],
            })
        except Exception as e:
            print("Nomba error", e)

        await send_fn(seller_phone, SCRIPTS["seller"]["onboarding_done"](seller["shop_name"]))

    elif step == "PRODUCT_NAME":
        prod_key = f"product_add:{seller_phone}"
        prod_state = json.loads(r.get(prod_key) or "{}")
        prod_state["name"] = t
        prod_state["step"] = "PRICE"
        r.setex(prod_key, 1800, json.dumps(prod_state))
        await send_fn(seller_phone, SCRIPTS["seller"]["product_name_received"]())

    elif step == "PRODUCT_PRICE":
        cleaned = t.replace(",", "").replace("\u20a6", "").replace("N", "")
        if not cleaned.isdigit():
            await send_fn(seller_phone, SCRIPTS["seller"]["invalid_price"]())
            return
        price_kobo = int(cleaned) * 100
        prod_key = f"product_add:{seller_phone}"
        prod_state = json.loads(r.get(prod_key) or "{}")
        seller = await get_seller_by_phone(seller_phone)
        await create_product(
            seller["_id"],
            prod_state["name"],
            price_kobo,
            10,
            prod_state.get("photo_url", ""),
        )
        r.delete(prod_key)
        await send_fn(seller_phone, SCRIPTS["seller"]["product_saved"](
            prod_state["name"], int(cleaned)
        ))
