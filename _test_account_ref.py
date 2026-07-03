import json
import asyncio
from src.db.queries import get_sellers, get_pending_order_for_seller
from src.handlers.nomba import verify_nomba_signature
from src.lib.config import get_settings

async def main():
    settings = get_settings()
    sellers = await get_sellers()
    print("Sellers:")
    for s in sellers:
        ref = "hustaq-seller-%s" % s['id']
        if len(ref) < 16:
            ref = ref.ljust(16, "0")
        print("  id=%s ref=%s shop=%s" % (s['id'], ref, s['shop_name']))

    target_ref = "hustaq-seller-6a467b4b1cd465730cda195b"
    for s in sellers:
        ref = "hustaq-seller-%s" % s['id']
        if len(ref) < 16:
            ref = ref.ljust(16, "0")
        if ref == target_ref:
            order = await get_pending_order_for_seller(s['id'])
            print("Matched seller: id=%s" % s['id'])
            print("Pending order: %s" % order)
        else:
            print("No match: %s vs %s" % (ref, target_ref))

    # Also test the actual webhook endpoint
    import urllib.request
    payload = {
        "event_type": "payment_success",
        "requestId": "NOM-TEST-ACCT-REF",
        "data": {
            "merchant": {"walletId": "wallet-x", "walletBalance": 100000, "userId": "user-x"},
            "terminal": {},
            "transaction": {
                "sessionId": "NOM-TEST-ACCT-REF",
                "type": "vact_transfer",
                "transactionId": "NOM-TEST-ACCT-REF",
                "responseCode": "",
                "originatingFrom": "api",
                "transactionAmount": 17000.0,
                "narration": "test",
                "time": "2026-07-03T10:51:44Z",
                "aliasAccountReference": target_ref,
                "aliasAccountType": "VIRTUAL",
                "aliasAccountNumber": "5343270516",
                "aliasAccountName": "Nomba/Test Shop",
            },
            "customer": {"senderName": "Test Buyer"},
        },
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "http://localhost:8001/api/webhooks/nomba",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=25) as resp:
        print("Response: %s %s" % (resp.status, resp.read().decode()[:200]))

asyncio.run(main())
