from src.db.client import get_db
from datetime import datetime, timezone

# --- Sellers ---
async def get_seller_by_phone(phone_number: str) -> dict | None:
    return await get_db().sellers.find_one({"phone_number": phone_number})

async def get_seller_by_bot_number(wa_number: str) -> dict | None:
    return await get_db().sellers.find_one({"wa_number": wa_number})

async def create_seller(phone_number: str, shop_name: str, shop_slug: str) -> dict:
    doc = {
        "phone_number": phone_number,
        "shop_name": shop_name,
        "shop_slug": shop_slug,
        "category": "",
        "location": "",
        "wa_number": "",
        "bot_paused": False,
        "balance_kobo": 0,
        "pending_balance_kobo": 0,
        "nomba_virtual_account": None,
        "nomba_bank_name": None,
        "nomba_bank_code": None,
        "created_at": datetime.now(timezone.utc),
    }
    result = await get_db().sellers.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc

async def update_seller(seller_id, updates: dict):
    await get_db().sellers.update_one({"_id": seller_id}, {"$set": updates})


async def get_seller_by_id(seller_id) -> dict | None:
    return await get_db().sellers.find_one({"_id": seller_id})


async def increment_seller_balance(seller_id, amount_kobo: int):
    await get_db().sellers.update_one(
        {"_id": seller_id}, {"$inc": {"balance_kobo": amount_kobo}}
    )


async def get_sellers() -> list[dict]:
    return await get_db().sellers.find().to_list(length=500)


async def get_pending_order_for_seller(seller_id) -> dict | None:
    return await get_db().orders.find_one(
        {"seller_id": seller_id, "status": "pending"},
        sort=[("created_at", -1)],
    )

# --- Products ---
async def get_products_by_seller(seller_id) -> list[dict]:
    cursor = get_db().products.find({"seller_id": seller_id, "visible": True}).sort("created_at", 1)
    return await cursor.to_list(length=100)

async def create_product(seller_id, name: str, price_kobo: int, stock_count: int, photo_url: str) -> dict:
    doc = {
        "seller_id": seller_id,
        "name": name,
        "price_kobo": price_kobo,
        "stock_count": stock_count,
        "photo_url": photo_url,
        "visible": True,
        "created_at": datetime.now(timezone.utc),
    }
    result = await get_db().products.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc

async def get_product_by_id(product_id) -> dict | None:
    return await get_db().products.find_one({"_id": product_id})

# --- Conversations ---
async def get_conversation(seller_id, buyer_phone: str) -> dict | None:
    return await get_db().conversations.find_one({
        "seller_id": seller_id,
        "buyer_phone": buyer_phone,
    })

async def create_conversation(seller_id, seller_wa: str, buyer_phone: str) -> dict:
    doc = {
        "seller_id": seller_id,
        "seller_whatsapp_number": seller_wa,
        "buyer_phone": buyer_phone,
        "state": "idle",
        "cart": {},
        "selected_product": None,
        "pending_order_id": None,
        "handoff_active": False,
        "last_message_at": datetime.now(timezone.utc),
    }
    result = await get_db().conversations.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc

async def update_conversation(conv_id, updates: dict):
    updates["last_message_at"] = datetime.now(timezone.utc)
    await get_db().conversations.update_one({"_id": conv_id}, {"$set": updates})

# --- Orders ---
async def create_order(seller_id, buyer_phone: str, items: list, subtotal_kobo: int,
                       total_kobo: int, delivery_address: str) -> dict:
    order_count = await get_db().orders.count_documents({"seller_id": seller_id})
    doc = {
        "order_number": f"ORD-{order_count + 1:03d}",
        "seller_id": seller_id,
        "buyer_phone": buyer_phone,
        "items": items,
        "subtotal_kobo": subtotal_kobo,
        "total_kobo": total_kobo,
        "status": "pending",
        "payment_status": "unpaid",
        "nomba_reference": None,
        "delivery_address": delivery_address,
        "created_at": datetime.now(timezone.utc),
    }
    result = await get_db().orders.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc

async def get_order_by_id(order_id) -> dict | None:
    return await get_db().orders.find_one({"_id": order_id})

async def get_orders_by_seller(seller_id, limit: int = 5) -> list[dict]:
    cursor = get_db().orders.find({"seller_id": seller_id}).sort("created_at", -1).limit(limit)
    return await cursor.to_list(length=limit)

async def update_order(order_id, updates: dict):
    await get_db().orders.update_one({"_id": order_id}, {"$set": updates})

# --- Payments ---
async def create_payment(order_id, seller_id, buyer_phone: str, amount_kobo: int, nomba_reference: str, status: str = "pending") -> dict:
    doc = {
        "order_id": order_id,
        "seller_id": seller_id,
        "buyer_phone": buyer_phone,
        "amount_kobo": amount_kobo,
        "status": status,
        "nomba_reference": nomba_reference,
        "created_at": datetime.now(timezone.utc),
    }
    result = await get_db().payments.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc

async def get_payment_by_reference(nomba_reference: str) -> dict | None:
    return await get_db().payments.find_one({"nomba_reference": nomba_reference})

async def update_payment(payment_id, updates: dict):
    await get_db().payments.update_one({"_id": payment_id}, {"$set": updates})
