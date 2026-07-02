from fastapi import APIRouter, Request, Response
from src.db.queries import (
    get_payment_by_reference, create_payment,
    get_order_by_id, update_order,
    update_seller, get_seller_by_phone,
)
from src.services.twilio import send_message
from src.bot.scripts import SCRIPTS
from src.lib.redis_client import get_redis
from bson import ObjectId

router = APIRouter()


@router.post("/nomba")
async def nomba_webhook(request: Request):
    body = await request.json()
    event = body.get("event")

    if event != "payment.success":
        return Response(content="", status_code=200)

    data = body["data"]
    reference = data["reference"]

    # Idempotency — Redis fast check + MongoDB fallback
    r = get_redis()
    idem_key = f"nomba:processed:{reference}"
    if r.get(idem_key):
        return Response(content="", status_code=200)

    existing = await get_payment_by_reference(reference)
    if existing:
        r.setex(idem_key, 86400, "1")
        return Response(content="", status_code=200)

    # Mark as processing immediately
    r.setex(idem_key, 86400, "1")

    order_id = ObjectId(data["orderId"])
    amount_kobo = int(float(data["amount"]) * 100)
    customer = data.get("customer", {})

    order = await get_order_by_id(order_id)
    if not order:
        return Response(content="", status_code=404)

    # Create payment record
    await create_payment(
        order_id, order["seller_id"],
        customer.get("phone", ""), amount_kobo, reference
    )

    # Update order
    await update_order(order_id, {"status": "paid", "payment_status": "paid"})

    # Update seller balance
    await update_seller(order["seller_id"], {
        "$inc": {"balance_kobo": amount_kobo}
    })

    # Notify buyer
    effective_buyer = customer.get("phone", "") or order.get("buyer_phone", "")
    if effective_buyer:
        await send_message(effective_buyer, SCRIPTS["buyer"]["CONFIRM_received"](order["order_number"]))

    # Notify seller
    seller = await get_seller_by_phone(order["seller_id"])
    if seller:
        await send_message(seller["phone_number"], SCRIPTS["seller"]["new_order"](
            order["order_number"], amount_kobo // 100,
            effective_buyer, order.get("delivery_address", ""),
        ))

    return Response(content="", status_code=200)
