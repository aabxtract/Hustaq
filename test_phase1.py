"""
Hustaq Phase 1 — Meta WhatsApp Cloud API Test Script
======================================================
Tests the Meta WhatsApp Cloud API webhook against your local server
to verify the full Phase 1 buyer/seller flow.

Supports:
  - Meta webhook verification (GET with hub.challenge)
  - Meta-format JSON POST payloads (as Meta would send them)
  - Legacy Twilio form-encoded POST payloads

Usage:
  1. Start the server:  uvicorn main:app --port 8001
  2. Seed the database:  python seed.py
  3. Run tests:          python test_phase1.py

Set FORMAT=meta or FORMAT=twilio env to choose payload format (default: meta).
Set TEST_URL=<url> to override the base URL (default: http://localhost:8001).
"""

import sys
import urllib.request
import urllib.parse
import json
import time
import os

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# ── Config ──────────────────────────────────────────────────────────────────
BASE_URL = os.environ.get("TEST_URL", "http://localhost:8001")
PAYLOAD_FORMAT = os.environ.get("FORMAT", "meta").lower()  # "meta" or "twilio"

HUSTAQ_NUMBER = "+2347074270520"      # Hustaq bot display number — seller management
SELLER_TWILIO = "+2347074270520"      # Seeded seller's twilio_number — buyer messages
BUYER_PHONE = "+2340000000001"        # Fake buyer phone for testing
SELLER_PHONE = "+2348012345678"       # Seeded demo seller phone
META_VERIFY_TOKEN = "hustaq_123"      # Must match .env META_VERIFY_TOKEN
# ────────────────────────────────────────────────────────────────────────────

PASS = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"
INFO = "\033[94m→\033[0m"


# ── Meta API payload builder ─────────────────────────────────────────────────

def build_meta_payload(from_phone: str, to_phone: str, body: str, msg_type: str = "text") -> dict:
    """Build a payload in Meta WhatsApp Cloud API webhook JSON format."""
    clean_from = from_phone.replace("whatsapp:", "")
    clean_to = to_phone.replace("whatsapp:", "")
    return {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {
                        "display_phone_number": clean_to,
                        "phone_number_id": "PHONE_NUMBER_ID"
                    },
                    "contacts": [{
                        "profile": {"name": "Test User"},
                        "wa_id": clean_from
                    }],
                    "messages": [{
                        "from": clean_from,
                        "id": f"wamid.test.{int(time.time())}",
                        "timestamp": str(int(time.time())),
                        "type": msg_type,
                        "text": {"body": body}
                    }]
                },
                "field": "messages"
            }]
        }]
    }


def send_twilio_webhook(from_phone, to_phone, body, num_media=0):
    """Simulate a Twilio WhatsApp webhook POST."""
    data = urllib.parse.urlencode({
        "From": f"whatsapp:{from_phone}",
        "To": f"whatsapp:{to_phone}",
        "Body": body,
        "NumMedia": str(num_media),
        "MessageSid": f"SMtest{int(time.time())}",
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{BASE_URL}/api/webhooks/twilio",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()
    except Exception as ex:
        return 0, str(ex)


def send_meta_webhook(from_phone, to_phone, body):
    """Send a payload in Meta WhatsApp Cloud API JSON format."""
    payload = build_meta_payload(from_phone, to_phone, body)
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/api/webhooks/twilio",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()
    except Exception as ex:
        return 0, str(ex)


def send_meta_verify_request():
    """Simulate Meta webhook verification GET request (hub.challenge)."""
    url = (
        f"{BASE_URL}/api/webhooks/twilio"
        f"?hub.mode=subscribe"
        f"&hub.verify_token={META_VERIFY_TOKEN}"
        f"&hub.challenge=1234567890"
    )
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode()
            return resp.status, body
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()
    except Exception as ex:
        return 0, str(ex)


def check_health():
    req = urllib.request.Request(f"{BASE_URL}/api/health", method="GET")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read())
            return body.get("status") == "ok"
    except Exception as ex:
        print(f"  {FAIL} Health check failed: {ex}")
        return False


def run_test(label, from_phone, to_phone, msg, expected_status=200):
    """Send a webhook in the configured format and check the status code."""
    if PAYLOAD_FORMAT == "meta":
        status, body = send_meta_webhook(from_phone, to_phone, msg)
    else:
        status, body = send_twilio_webhook(from_phone, to_phone, msg)
    icon = PASS if status == expected_status else FAIL
    print(f"  {icon} [{status}] {label}")
    if status != expected_status:
        print(f"       Response: {body[:300]}")
    time.sleep(0.5)
    return status == expected_status


def run_verify_test():
    """Test Meta webhook verification (GET)."""
    status, body = send_meta_verify_request()
    icon = PASS if status == 200 and body == "1234567890" else FAIL
    print(f"  {icon} [{status}] Meta webhook verification (GET)")
    if status != 200 or body != "1234567890":
        print(f"       Expected challenge '1234567890', got: {body[:100]}")
    time.sleep(0.3)
    return status == 200 and body == "1234567890"


def main():
    fmt_label = "Meta JSON format" if PAYLOAD_FORMAT == "meta" else "Twilio form-encoded format"
    print("\n================================================")
    print("  Hustaq Phase 1 — Meta API Tests")
    print(f"  Payload format: {fmt_label}")
    print(f"  Server:         {BASE_URL}")
    print("================================================\n")

    # 0. Health check
    print(f"{INFO} Step 0: Health check")
    if check_health():
        print(f"  {PASS} Server is alive at {BASE_URL}")
    else:
        print(f"  {FAIL} Server not responding — start with: uvicorn main:app --port 8001")
        return
    print()

    # 1. Meta webhook verification
    print(f"{INFO} Step 0.5: Meta webhook verification (GET)")
    run_verify_test()
    print()

    # 2. Seller command: existing seeded seller sends MENU
    print(f"{INFO} Step 1: Seller texts MENU (seeded seller)")
    run_test("Seller menu command", SELLER_PHONE, HUSTAQ_NUMBER, "MENU")
    print()

    # 3. Buyer flow
    print(f"{INFO} Step 2: Buyer sends 'Hi' -> should get product catalog")
    run_test("Buyer greeting", BUYER_PHONE, SELLER_TWILIO, "Hi")

    print(f"{INFO} Step 3: Buyer selects product 1")
    run_test("Buyer selects product", BUYER_PHONE, SELLER_TWILIO, "1")

    print(f"{INFO} Step 4: Buyer taps 'Buy now' (option 1)")
    run_test("Buyer buy now", BUYER_PHONE, SELLER_TWILIO, "1")

    print(f"{INFO} Step 5: Buyer enters quantity")
    run_test("Buyer enters qty", BUYER_PHONE, SELLER_TWILIO, "2")

    print(f"{INFO} Step 6: Buyer CONFIRMs cart")
    run_test("Buyer confirms cart", BUYER_PHONE, SELLER_TWILIO, "CONFIRM")

    print(f"{INFO} Step 7: Buyer provides delivery address")
    run_test("Buyer delivery address", BUYER_PHONE, SELLER_TWILIO, "12 Herbert Macaulay Way, Yaba Lagos")

    print(f"{INFO} Step 8: Buyer claims PAID (Phase 1 manual ack)")
    run_test("Buyer says PAID", BUYER_PHONE, SELLER_TWILIO, "PAID")
    print()

    # 4. New seller onboarding (unused phone number)
    NEW_SELLER = "+2349099998877"
    print(f"{INFO} Step 9: New seller onboarding flow")
    run_test("New seller first message", NEW_SELLER, HUSTAQ_NUMBER, "I want to sell")
    run_test("New seller says YES", NEW_SELLER, HUSTAQ_NUMBER, "YES")
    run_test("New seller sets shop name", NEW_SELLER, HUSTAQ_NUMBER, "Test Shop NG")
    run_test("New seller picks category", NEW_SELLER, HUSTAQ_NUMBER, "1")
    run_test("New seller sets location", NEW_SELLER, HUSTAQ_NUMBER, "Ikeja Lagos")
    print()

    # 5. Edge cases
    print(f"{INFO} Step 10: Edge cases")
    run_test("Gibberish from buyer", BUYER_PHONE, SELLER_TWILIO, "asdfghjkl")
    run_test("MENU resets buyer state", BUYER_PHONE, SELLER_TWILIO, "MENU")
    print()

    print("================================================")
    print("  Phase 1 tests complete!")
    print(f"  Format used: {fmt_label}")
    print("  Check server logs for reply messages.")
    print("================================================\n")


if __name__ == "__main__":
    main()
