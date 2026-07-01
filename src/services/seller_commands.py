from src.db.queries import (
    get_seller_by_phone, create_seller, update_seller,
    get_orders_by_seller, get_products_by_seller, create_product,
)
from src.bot.scripts import SCRIPTS
from src.services.twilio import send_message
from src.lib.config import settings

# In-memory onboarding state (for hackathon simplicity — no Redis needed)
# Maps phone_number -> onboarding step
_onboarding_state: dict[str, dict] = {}


async def handle_seller_command(seller_phone: str, text: str, media_url: str | None):
    seller = await get_seller_by_phone(seller_phone)

    if not seller:
        return await start_onboarding(seller_phone)

    # Check if seller is in onboarding flow
    if seller_phone in _onboarding_state:
        return await continue_onboarding(seller, seller_phone, text)

    cmd = text.strip().lower()

    if cmd in ("menu", "0"):
        await send_message(seller_phone, SCRIPTS["seller"]["menu"](seller["shop_name"]))
    elif cmd in ("2", "view orders"):
        orders = await get_orders_by_seller(seller["_id"])
        await send_message(seller_phone, SCRIPTS["seller"]["order_list"](orders))
    elif cmd in ("3", "check balance"):
        await send_message(seller_phone, SCRIPTS["seller"]["balance"](
            seller["balance_kobo"] // 100, seller["pending_balance_kobo"] // 100))
    elif cmd == "pause":
        await update_seller(seller["_id"], {"bot_paused": True})
        await send_message(seller_phone, SCRIPTS["seller"]["pause_confirmed"]())
    elif cmd == "resume":
        await update_seller(seller["_id"], {"bot_paused": False})
        await send_message(seller_phone, SCRIPTS["seller"]["resume_confirmed"]())
    elif media_url:
        await handle_product_photo(seller, seller_phone, media_url)
    else:
        await send_message(seller_phone, SCRIPTS["seller"]["menu"](seller["shop_name"]))


async def start_onboarding(seller_phone: str):
    seller = await create_seller(seller_phone, "New Shop", f"shop-{seller_phone[-4:]}")
    _onboarding_state[seller_phone] = {"step": "WELCOME", "seller_id": str(seller["_id"])}
    await send_message(seller_phone, SCRIPTS["seller"]["onboarding_welcome"]())


async def handle_product_photo(seller, seller_phone: str, media_url: str):
    # For hackathon MVP: store the Twilio media URL directly
    # No S3 needed — Twilio media URLs are accessible for a few days
    _onboarding_state[seller_phone] = {
        "step": "PRODUCT_NAME",
        "photo_url": media_url,
        "seller_id": str(seller["_id"]),
    }
    await send_message(seller_phone, "Got the photo! What is the product name?")


async def continue_onboarding(seller, seller_phone: str, text: str):
    state = _onboarding_state.get(seller_phone)
    if not state:
        return
        
    step = state["step"]

    if step == "WELCOME":
        if text.strip().lower() in ("yes", "y"):
            state["step"] = "SHOP_NAME"
            await send_message(seller_phone, SCRIPTS["seller"]["onboarding_shopname"]())
        else:
            await send_message(seller_phone, "Reply YES to get started!")
    elif step == "SHOP_NAME":
        state["shop_name"] = text.strip()
        state["step"] = "CATEGORY"
        await send_message(seller_phone, SCRIPTS["seller"]["onboarding_category"]())
    elif step == "CATEGORY":
        categories = {"1": "Fashion", "2": "Food and Drinks", "3": "Beauty", "4": "Gadgets", "5": "Other"}
        category = categories.get(text.strip(), "Other")
        await update_seller(seller["_id"], {
            "shop_name": state["shop_name"],
            "shop_slug": state["shop_name"].lower().replace(" ", "-"),
            "category": category,
        })
        state["step"] = "LOCATION"
        await send_message(seller_phone, SCRIPTS["seller"]["onboarding_location"]())
    elif step == "LOCATION":
        await update_seller(seller["_id"], {"location": text.strip()})
        from src.services.nomba import create_virtual_account
        try:
            acct = await create_virtual_account(str(seller["_id"]), state["shop_name"])
            await update_seller(seller["_id"], {
                "nomba_virtual_account": acct["account_number"],
                "nomba_bank_name": acct["bank_name"],
                "nomba_bank_code": acct["bank_code"],
            })
        except Exception as e:
            print("Nomba error", e)
        del _onboarding_state[seller_phone]
        await send_message(seller_phone, SCRIPTS["seller"]["onboarding_done"](state["shop_name"]))
    elif step == "PRODUCT_NAME":
        state["product_name"] = text.strip()
        state["step"] = "PRODUCT_PRICE"
        await send_message(seller_phone, "What is the price in Naira?")
    elif step == "PRODUCT_PRICE":
        price_kobo = int(text.strip()) * 100
        await create_product(
            seller["_id"],
            state["product_name"],
            price_kobo,
            10,  # default stock
            state["photo_url"],
        )
        del _onboarding_state[seller_phone]
        await send_message(seller_phone, f'{state["product_name"]} added to your shop!')
