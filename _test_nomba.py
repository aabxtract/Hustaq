import urllib.request
import urllib.error
import json

BASE_URL = "http://localhost:8001"

def send_nomba_webhook(alias_account_ref, amount_naira=17000.0, tx_id="NOM-TEST-P2-001"):
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
                "sessionId": tx_id,
                "type": "vact_transfer",
                "transactionId": tx_id,
                "responseCode": "",
                "originatingFrom": "api",
                "transactionAmount": amount_naira,
                "narration": "Phase 2 Buyer transfer %s" % amount_naira,
                "time": "2026-07-03T10:51:44Z",
                "aliasAccountReference": alias_account_ref,
                "aliasAccountType": "VIRTUAL",
                "aliasAccountNumber": "5343270516",
                "aliasAccountName": "Nomba/Test Shop",
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
        "%s/api/webhooks/nomba" % BASE_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            return resp.status, resp.read().decode()[:200]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:200]
    except Exception as ex:
        return 0, str(ex)[:200]

# Test with the actual seller account ref from the order
account_ref = "hustaq-seller-6a467b4b1cd465730cda195b"
status, body = send_nomba_webhook(account_ref, amount_naira=17000.0, tx_id="NOM-TEST-P2-001")
print("status=%s body=%s" % (status, body))
