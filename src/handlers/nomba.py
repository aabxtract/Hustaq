from fastapi import APIRouter, Request, Response
from src.db.queries import (
    get_payment_by_reference, create_payment,
    get_order_by_id, update_order,
    update_seller,
)
from src.services.twilio import send_message
from src.bot.scripts import SCRIPTS
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

    # Idempotency — check if already processed
    existing = await get_payment_by_reference(reference)
    if existing:
        return Response(content="", status_code=200)

    order_id = ObjectId(data["orderId"])
    amount_kobo = int(data["amount"])
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
    await send_message(customer.get("phone", ""), SCRIPTS["buyer"]["CONFIRM_received"](order["order_number"]))

    # Notify seller
    from src.db.queries import get_seller_by_phone
    seller = await get_seller_by_phone(order["seller_id"])
    if seller:
        await send_message(seller["phone_number"], SCRIPTS["seller"]["new_order"](
            order["order_number"], amount_kobo // 100,
            customer.get("phone", ""), order["delivery_address"]
        ))

    return Response(content="", status_code=200)
