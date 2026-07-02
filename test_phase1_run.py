"""
Hustaq Phase 1 — Meta WhatsApp Cloud API Test Runner
Runs Phase 1 tests using Meta JSON payloads against the local server.
"""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import urllib.request, urllib.error, json, time, os

BASE_URL = os.environ.get("TEST_URL", "http://localhost:8003")
PASS = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"
INFO = "\033[94m→\033[0m"

HUSTAQ_NUMBER = "+2347074270520"
SELLER_PHONE = "+2348012345678"
BUYER_PHONE = "+2340000000001"
NEW_SELLER = "+2349099998877"


def send_meta(from_phone, to_phone, body):
    payload = {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {"display_phone_number": to_phone, "phone_number_id": "PHONE_NUMBER_ID"},
                    "contacts": [{"profile": {"name": "Test User"}, "wa_id": from_phone}],
                    "messages": [{
                        "from": from_phone,
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
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/api/webhooks/whatsapp",
        data=data, headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:300]
    except Exception as ex:
        return 0, str(ex)[:300]


def run_step(label, from_phone, to_phone, msg, expected=200):
    status, body = send_meta(from_phone, to_phone, msg)
    icon = PASS if status == expected else FAIL
    print(f"  {icon} [{status}] {label}")
    if status != expected:
        print(f"       Response: {body}")
    time.sleep(0.8)
    return status == expected


def main():
    print(); print("=" * 50)
    print("  Hustaq Phase 1 — Meta API Tests")
    print(f"  Server: {BASE_URL}")
    print("=" * 50); print()

    # 0. Health check
    print(f"{INFO} Step 0: Health check")
    try:
        r = urllib.request.Request(f"{BASE_URL}/api/health", method="GET")
        with urllib.request.urlopen(r, timeout=10) as resp:
            body = json.loads(resp.read())
            if body.get("status") == "ok":
                print(f"  {PASS} Server is alive")
            else:
                print(f"  {FAIL} Health failed: {body}"); return
    except Exception as ex:
        print(f"  {FAIL} Server not responding: {ex}"); return
    print()

    # 0.5 Meta webhook verification
    print(f"{INFO} Step 0.5: Meta webhook verification (GET)")
    url = (f"{BASE_URL}/api/webhooks/whatsapp"
           f"?hub.mode=subscribe&hub.verify_token=hustaq_123"
           f"&hub.challenge=1234567890")
    try:
        r = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(r, timeout=10) as resp:
            challenge = resp.read().decode()
            ok = resp.status == 200 and challenge == "1234567890"
            print(f"  {PASS if ok else FAIL} [{resp.status}] Challenge={challenge}")
    except Exception as ex:
        print(f"  {FAIL} Verify failed: {ex}")
    print()

    # 1. Seller MENU
    print(f"{INFO} Step 1: Seller texts MENU")
    run_step("Seller menu command", SELLER_PHONE, HUSTAQ_NUMBER, "MENU")
    print()

    # 2. Buyer greeting
    print(f"{INFO} Step 2: Buyer sends 'Hi'")
    run_step("Buyer greeting", BUYER_PHONE, HUSTAQ_NUMBER, "Hi")
    print()

    # 3. Buyer selects product
    print(f"{INFO} Step 3: Buyer selects product 1")
    run_step("Buyer selects product", BUYER_PHONE, HUSTAQ_NUMBER, "1")
    print()

    # 4. Buyer buy now
    print(f"{INFO} Step 4: Buyer taps 'Buy now'")
    run_step("Buyer buy now", BUYER_PHONE, HUSTAQ_NUMBER, "1")
    print()

    # 5. Quantity
    print(f"{INFO} Step 5: Buyer enters quantity")
    run_step("Buyer enters qty", BUYER_PHONE, HUSTAQ_NUMBER, "2")
    print()

    # 6. CONFIRM
    print(f"{INFO} Step 6: Buyer CONFIRMs cart")
    run_step("Buyer confirms cart", BUYER_PHONE, HUSTAQ_NUMBER, "CONFIRM")
    print()

    # 7. Delivery address
    print(f"{INFO} Step 7: Buyer provides delivery address")
    run_step("Delivery address", BUYER_PHONE, HUSTAQ_NUMBER,
             "12 Herbert Macaulay Way, Yaba Lagos")
    print()

    # 8. PAID
    print(f"{INFO} Step 8: Buyer claims PAID")
    run_step("Buyer says PAID", BUYER_PHONE, HUSTAQ_NUMBER, "PAID")
    print()

    # 9. New seller onboarding
    print(f"{INFO} Step 9: New seller onboarding flow")
    run_step("First message", NEW_SELLER, HUSTAQ_NUMBER, "I want to sell")
    run_step("Says YES", NEW_SELLER, HUSTAQ_NUMBER, "YES")
    run_step("Shop name", NEW_SELLER, HUSTAQ_NUMBER, "Test Shop NG")
    run_step("Category", NEW_SELLER, HUSTAQ_NUMBER, "1")
    run_step("Location", NEW_SELLER, HUSTAQ_NUMBER, "Ikeja Lagos")
    print()

    # 10. Edge cases
    print(f"{INFO} Step 10: Edge cases")
    run_step("Gibberish from buyer", BUYER_PHONE, HUSTAQ_NUMBER, "asdfghjkl")
    run_step("MENU resets buyer state", BUYER_PHONE, HUSTAQ_NUMBER, "MENU")
    print()

    print("=" * 50)
    print("  Phase 1 tests complete!")
    print("  Check server logs for sent replies.")
    print("=" * 50); print()


if __name__ == "__main__":
    main()
