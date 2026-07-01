import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

"""
Hustaq Phase 1 Test Script
===========================
Simulates Twilio webhook calls against your live Lambda to test the full
buyer flow without needing a real phone.

Usage:
    python test_phase1.py

Make sure SKIP_TWILIO_VERIFY=true is set in your Lambda env vars,
otherwise the signature check will reject these test requests.
"""

import sys
import urllib.request
import urllib.parse
import json
import time

# Force UTF-8 output so the status symbols (✓✗→) render on Windows consoles
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# ── Config ──────────────────────────────────────────────────────────────────
import os as _os
LAMBDA_URL = "http://127.0.0.1:8001"  # Local server; swap back to AWS URL for prod)
HUSTAQ_NUMBER    = "+14155238886"     # Hustaq central number — seller management
SELLER_TWILIO    = "+14155238886"     # Seeded seller's twilio_number — buyer messages
BUYER_PHONE      = "+2340000000001"   # Fake buyer phone for testing
SELLER_PHONE     = "+2348012345678"   # Seeded demo seller phone
# ────────────────────────────────────────────────────────────────────────────

PASS = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"
INFO = "\033[94m→\033[0m"


def send_twilio_webhook(from_phone: str, to_phone: str, body: str, num_media: int = 0) -> tuple[int, str]:
    """Simulate a Twilio WhatsApp webhook POST."""
    data = urllib.parse.urlencode({
        "From": f"whatsapp:{from_phone}",
        "To":   f"whatsapp:{to_phone}",
        "Body": body,
        "NumMedia": str(num_media),
        "MessageSid": f"SMtest{int(time.time())}",
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{LAMBDA_URL}/webhooks/twilio",
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


def check_health() -> bool:
    req = urllib.request.Request(f"{LAMBDA_URL}/health", method="GET")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read())
            return body.get("status") == "ok"
    except Exception as ex:
        print(f"  {FAIL} Health check failed: {ex}")
        return False


def run_test(label: str, from_phone: str, to_phone: str, msg: str, expected_status: int = 200):
    status, body = send_twilio_webhook(from_phone, to_phone, msg)
    icon = PASS if status == expected_status else FAIL
    print(f"  {icon} [{status}] {label}")
    if status != expected_status:
        print(f"       Response: {body[:300]}")
    time.sleep(0.8)   # avoid hammering Lambda cold start
    return status == expected_status


# ── Test Suite ───────────────────────────────────────────────────────────────

def main():
    print("\n========================================")
    print("  Hustaq Phase 1 — Live Lambda Tests")
    print("========================================\n")

    # 1. Health
    print(f"{INFO} Step 0: Health check")
    if check_health():
        print(f"  {PASS} Lambda is alive")
    else:
        print(f"  {FAIL} Lambda not responding — check URL + deployment")
        return
    print()

    # 2. Seller command: existing seeded seller sends MENU
    print(f"{INFO} Step 1: Seller texts MENU (seeded seller)")
    run_test("Seller menu command", SELLER_PHONE, HUSTAQ_NUMBER, "MENU")
    print()

    # 3. Buyer flow
    print(f"{INFO} Step 2: Buyer sends 'Hi' → should get product catalog")
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

    print("========================================")
    print("  Done! Check your WhatsApp & CloudWatch")
    print("  for actual bot reply messages.")
    print("========================================\n")


if __name__ == "__main__":
    main()
