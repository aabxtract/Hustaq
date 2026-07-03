import hmac
import hashlib
import base64
from fastapi import APIRouter, Request, Response
from src.db.queries import (
    get_payment_by_reference, create_payment,
    get_order_by_id, update_order,
    update_seller, get_seller_by_id, get_sellers,
    get_pending_order_for_seller,
    increment_seller_balance,
)
from src.services.whatsapp import send_message
from src.bot.scripts import SCRIPTS
from src.lib.redis_client import get_redis
from src.lib.config import get_settings

router = APIRouter()


def verify_nomba_signature(payload: dict, signature: str, secret: str, timestamp: str) -> bool:
    data = payload.get("data", {})
    merchant = data.get("merchant", {})
    transaction = data.get("transaction", {})

    event_type = payload.get("event_type", "")
    request_id = payload.get("requestId", "")
    user_id = merchant.get("userId", "")
    wallet_id = merchant.get("walletId", "")
    transaction_id = transaction.get("transactionId", "")
    transaction_type = transaction.get("type", "")
    transaction_time = transaction.get("time", "")
    transaction_response_code = transaction.get("responseCode", "")

    if transaction_response_code == "null":
        transaction_response_code = ""

    hashing_payload = (
        f"{event_type}:{request_id}:{user_id}:{wallet_id}:"
        f"{transaction_id}:{transaction_type}:{transaction_time}:"
        f"{transaction_response_code}:{timestamp}"
    )

    digest = hmac.new(
        secret.encode("utf-8"),
        hashing_payload.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    expected_signature = base64.b64encode(digest).decode("utf-8")

    return hmac.compare_digest(expected_signature.lower(), signature.lower())


@router.post("/nomba")
async def nomba_webhook(request: Request):
    body = await request.json()
    webhook_secret = get_settings().NOMBA_WEBHOOK_SECRET

    # 1. Verify webhook signature if secret is configured
    if webhook_secret:
        signature = request.headers.get("nomba-signature", "")
        timestamp = request.headers.get("nomba-timestamp", "")
        if not verify_nomba_signature(body, signature, webhook_secret, timestamp):
            return Response(content="", status_code=403)

    event_type = body.get("event_type")

    if event_type != "payment_success":
        return Response(content="", status_code=200)

    data = body["data"]
    transaction = data["transaction"]

    tx_id = transaction["transactionId"]
    account_ref = transaction["aliasAccountReference"]
    amount_naira = transaction["transactionAmount"]
    amount_kobo = int(amount_naira * 100)
    sender_name = data.get("customer", {}).get("senderName", "")

    # 2. Idempotency — Redis fast check + MongoDB fallback
    r = get_redis()
    idem_key = f"nomba:processed:{tx_id}"
    if r.get(idem_key):
        return Response(content="", status_code=200)

    existing = await get_payment_by_reference(tx_id)
    if existing:
        r.setex(idem_key, 86400, "1")
        return Response(content="", status_code=200)

    # Mark as processing immediately
    r.setex(idem_key, 86400, "1")

    # 3. Find seller by accountRef
    sellers = await get_sellers()
    seller = None
    for s in sellers:
        ref = f"hustaq-seller-{s['id']}"
        if len(ref) < 16:
            ref = ref.ljust(16, "0")
        if ref == account_ref:
            seller = s
            break

    if not seller:
        return Response(content="", status_code=200)

    # 4. Find pending order for this seller (most recent)
    order = await get_pending_order_for_seller(seller["id"])
    if not order:
        return Response(content="", status_code=200)

    # Create payment record
    await create_payment(
        order["_id"], seller["id"],
        "", amount_kobo, tx_id
    )

    # Update order
    await update_order(order["_id"], {"status": "pending", "payment_status": "paid"})

    # Update seller balance
    await increment_seller_balance(seller["id"], amount_kobo)

    # Notify buyer
    effective_buyer = order.get("buyer_phone", "")
    if effective_buyer:
        await send_message(effective_buyer, SCRIPTS["buyer"]["CONFIRM_RECEIVED"](order["order_number"]))

    # Notify seller
    if seller:
        await send_message(seller["phone_number"], SCRIPTS["seller"]["new_order"](
            order["order_number"], amount_kobo // 100,
            sender_name, order.get("delivery_address", ""),
        ))

    return Response(content="", status_code=200)

