import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URI = "mongodb+srv://hesedanu_db_user:MT7XVyKGSzrzAx9B@cluster0.dz7e9vn.mongodb.net/?appName=Cluster0&serverSelectionTimeoutMS=5000&tlsInsecure=true"

async def main():
    client = AsyncIOMotorClient(MONGO_URI)
    db = client.hustaq
    orders = await db.orders.find({"buyer_phone": "+2340000000001"}).sort([("created_at", -1)]).limit(3).to_list(3)
    for o in orders:
        print("order=%s status=%s payment=%s nomba_ref=%s seller_id=%s" % (o.get('order_number'), o.get('status'), o.get('payment_status'), o.get('nomba_reference'), o.get('seller_id')))
        for p in await db.payments.find({"order_id": o["_id"]}).to_list(10):
            print("  payment status=%s ref=%s amount=%s buyer=%s" % (p.get('status'), p.get('nomba_reference'), p.get('amount_kobo'), p.get('buyer_phone')))
    seller = orders[0].get("seller_id") if orders else None
    if seller:
        s = await db.sellers.find_one({"_id": seller})
        if s:
            print("seller balance=%s shop=%s wa=%s" % (s.get('balance_kobo'), s.get('shop_name'), s.get('wa_number')))
        products = await db.products.find({"seller_id": seller}).to_list(10)
        for p in products:
            print("  product name=%s price=%s stock=%s" % (p.get('name'), p.get('price_kobo'), p.get('stock_count')))
    latest = orders[0] if orders else None
    if latest:
        print("LATEST_ORDER_NUMBER=%s" % latest['order_number'])
        print("LATEST_SELLER_ID=%s" % latest['seller_id'])
        print("LATEST_BUYER_PHONE=%s" % latest['buyer_phone'])
        print("LATEST_TOTAL_Kobo=%s" % latest['total_kobo'])
    client.close()

asyncio.run(main())


