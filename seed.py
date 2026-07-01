import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from datetime import datetime, timezone

async def seed():
    client = AsyncIOMotorClient(os.environ["MONGODB_URI"])
    db = client.hustaq

    # Seed seller
    await db.sellers.update_one(
        {"phone_number": "+2348012345678"},
        {"$setOnInsert": {
            "phone_number": "+2348012345678",
            "shop_name": "Amina Fabrics",
            "shop_slug": "amina-fabrics",
            "category": "fashion",
            "location": "Yaba Lagos",
            "twilio_number": os.environ["TWILIO_WHATSAPP_NUMBER"],
            "bot_paused": False,
            "balance_kobo": 0,
            "pending_balance_kobo": 0,
            "nomba_virtual_account": None,
            "nomba_bank_name": None,
            "nomba_bank_code": None,
            "created_at": datetime.now(timezone.utc),
        }},
        upsert=True,
    )

    seller = await db.sellers.find_one({"shop_slug": "amina-fabrics"})

    # Seed product
    await db.products.update_one(
        {"seller_id": seller["_id"], "name": "Hollandaise Ankara"},
        {"$setOnInsert": {
            "seller_id": seller["_id"],
            "name": "Hollandaise Ankara",
            "price_kobo": 850000,
            "stock_count": 20,
            "photo_url": "https://placehold.co/400",
            "visible": True,
            "created_at": datetime.now(timezone.utc),
        }},
        upsert=True,
    )

    print("Seed complete!")
    client.close()

if __name__ == "__main__":
    asyncio.run(seed())
