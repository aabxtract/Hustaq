"""
Hustaq Phase 2 — Nomba Integration Test Script
================================================
"""
import sys
import urllib.request
import urllib.error
import json
import time
import os
from dotenv import load_dotenv
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
load_dotenv()
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
BASE_URL = os.environ.get("TEST_URL", "http://localhost:8001")
HUSTAQ_NUMBER = os.environ.get("META_BOT_NUMBER", "+15556307807")
BUYER_PHONE = "+2340000000001"
MONGODB_URI = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/hustaq")
PASS = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"
INFO = "\033[94m→\033[0m"

def build_meta_payload(from_phone: str, to_phone: str, body: str) -> dict:
    clean_from = from_phone.replace("whatsapp:", "")
    clean_to = to_phone.replace("whatsapp:", "")
    return {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {"display_phone_number": clean_to, "phone_number_id": "PHONE_NUMBER_ID"},
                    "contacts": [{"profile": {"name": "Test User"}, "wa_id": clean_from}],
                    "messages": [{
                        "from": clean_from,
                        "id": f"wamid.test.{int(time.time())}",
                        "timestamp": str(int(time.time())),
                        "type": "text",
                        "text": {"body": body}
                    }]
                },
                "field": "messages"
            }]
        }]
    }

def send_webhook(from_phone: str, to_phone: str, body: str):
    payload = build_meta_payload(from_phone, to_phone, body)
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/api/webhooks/whatsapp",
        data=data, headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            return resp.status, resp.read().decode()[:200]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:200]
    except Exception as ex:
        return 0, str(ex)[:200]

def send_nomba_webhook(alias_account_ref: str, amount_naira: float = 170.0, tx_id: str = "NOM-TEST-P2-001"):
    payload = {
        "event_type": "payment_success",
        "requestId": tx_id,
        "data": {
            "merchant": {
                "walletId": "wallet-" + tx_id,
                "walletBalance": 100000,
                "userId": "user-" + tx_id,
            },
            "terminal": {},
            "transaction": {
                "aliasAccountNumber": "5343270516",
                "fee": 5,
                "sessionId": tx_id,
                "type": "vact_transfer",
                "transactionId": tx_id,
                "aliasAccountName": "Nomba/Test Shop",
                "responseCode": "",
                "originatingFrom": "api",
                "transactionAmount": amount_naira,
                "narration": f"Phase 2 Buyer transfer {amount_naira}",
                "time": "2026-07-03T10:51:44Z",
                "aliasAccountReference": alias_account_ref,
                "aliasAccountType": "VIRTUAL",
            },
            "customer": {
                "bankCode": "090645",
                "senderName": "Phase 2 Buyer",
                "bankName": "Nombank",
                "accountNumber": "0000000000",
            },
        },
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/api/webhooks/nomba",
        data=data, headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            return resp.status, resp.read().decode()[:200]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:200]
    except Exception as ex:
        return 0, str(ex)[:200]

async def get_latest_order(buyer_phone: str):
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client.hustaq
    order = await db.orders.find_one({"buyer_phone": buyer_phone}, sort=[("created_at", -1)])
    client.close()
    return order

async def get_seller(seller_id):
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client.hustaq
    seller = await db.sellers.find_one({"_id": seller_id})
    client.close()
    return seller

async def get_payments_for_order(order_id):
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client.hustaq
    payments = await db.payments.find({"order_id": order_id}).to_list(length=10)
    client.close()
    return payments

def run_step(label, from_phone, to_phone, msg, expected=200):
    status, body = send_webhook(from_phone, to_phone, msg)
    icon = PASS if status == expected else FAIL
    print(f"  {icon} [{status}] {label}")
    if status != expected:
        print(f"       Response: {body}")
    time.sleep(0.8)
    return status == expected

def main():
    print("\n================================================")
    print("  Hustaq Phase 2 — Nomba Integration Tests")
    print(f"  Server: {BASE_URL}")
    print("================================================\n")

    print(f"{INFO} Step 0: Health check")
    try:
        req = urllib.request.Request(f"{BASE_URL}/api/health", method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read())
            if body.get("status") == "ok":
                print(f"  {PASS} Server is alive")
            else:
                print(f"  {FAIL} Health failed: {body}")
                return
    except Exception as ex:
        print(f"  {FAIL} Server not responding: {ex}")
        return
    print()

    print(f"{INFO} Step 1: Buyer creates order on {HUSTAQ_NUMBER}")
    run_step("Buyer greeting", BUYER_PHONE, HUSTAQ_NUMBER, "Hi")
    run_step("Buyer selects product", BUYER_PHONE, HUSTAQ_NUMBER, "1")
    run_step("Buyer buy now", BUYER_PHONE, HUSTAQ_NUMBER, "1")
    run_step("Buyer enters qty", BUYER_PHONE, HUSTAQ_NUMBER, "2")
    run_step("Buyer confirms cart", BUYER_PHONE, HUSTAQ_NUMBER, "CONFIRM")
    run_step("Delivery address", BUYER_PHONE, HUSTAQ_NUMBER, "12 Herbert Macaulay Way, Yaba Lagos")
    run_step("Buyer says PAID", BUYER_PHONE, HUSTAQ_NUMBER, "PAID")
    print()

    print(f"{INFO} Step 2: Query latest order from MongoDB")
    try:
        order = asyncio.run(get_latest_order(BUYER_PHONE))
        if not order:
            print(f"  {FAIL} No order found for buyer {BUYER_PHONE}")
            return
        print(f"  {PASS} Order found: {order.get('order_number')} (id={order.get('_id')})")
        print(f"       status={order.get('status')} payment_status={order.get('payment_status')}")
        order_id_str = str(order["_id"])
        seller_id = str(order.get("seller_id", ""))
    except Exception as ex:
        print(f"  {FAIL} DB query failed: {ex}")
        return
    print()

    print(f"{INFO} Step 3: Simulate Nomba payment.success webhook")
    ref = "NOM-TEST-P2-001"
    account_ref = f"hustaq-seller-{seller_id}"
    if len(account_ref) < 16:
        account_ref = account_ref.ljust(16, "0")
    status, body = send_nomba_webhook(account_ref, amount_naira=170.0, tx_id=ref)
    icon = PASS if status == 200 else FAIL
    print(f"  {icon} [{status}] POST /api/webhooks/nomba")
    if status != 200:
        print(f"       Response: {body}")
    print()

    print(f"{INFO} Step 4: Verify post-webhook DB state")
    try:
        updated_order = asyncio.run(get_latest_order(BUYER_PHONE))
        payments = asyncio.run(get_payments_for_order(updated_order["_id"]))
        seller_id = updated_order.get("seller_id")
        seller = asyncio.run(get_seller(seller_id)) if seller_id else None

        order_ok = updated_order.get("status") == "paid" and updated_order.get("payment_status") == "paid"
        payment_ok = len(payments) == 1 and payments[0].get("status") == "success"
        balance_ok = False
        if seller:
            balance_ok = seller.get("balance_kobo", 0) >= updated_order.get("total_kobo", 0)

        print(f"  {'✓' if order_ok else '✗'} order.status={updated_order.get('status')} payment_status={updated_order.get('payment_status')}")
        print(f"  {'✓' if payment_ok else '✗'} payments={len(payments)} status={payments[0].get('status') if payments else 'missing'}")
        print(f"  {'✓' if balance_ok else '✗'} seller_balance={seller.get('balance_kobo', 0) if seller else 'N/A'}")

        if order_ok and payment_ok and balance_ok:
            print(f"\n  {PASS} Phase 2 webhook logic verified")
        else:
            print(f"\n  {FAIL} Phase 2 post-webhook checks failed")
    except Exception as ex:
        print(f"  {FAIL} DB verification failed: {ex}")
    print()

    print("================================================")
    print("  Phase 2 tests complete!")
    print("================================================")
    print()

if __name__ == "__main__":
    main()
