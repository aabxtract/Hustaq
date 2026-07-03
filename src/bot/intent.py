from typing import Literal

Intent = Literal[
    "BROWSE", "SELECT", "QUANTITY", "CHECKOUT", "CONFIRM",
    "CANCEL", "GREETING", "HANDOFF", "TRACK", "PAID", "MENU",
    "QUESTION", "UNKNOWN"
]

# Button IDs from interactive messages
BUTTON_IDS = {
    "buy_now", "ask_question", "back_to_catalog",
    "confirm_order", "cancel_order", "paid",
    "menu", "track", "help",
    "add_product", "view_orders", "check_balance", "pause_bot", "resume_bot",
    "onboard_yes", "onboard_no",
}

PATTERNS: dict[str, list[str]] = {
    "GREETING": ["hi", "hello", "hey", "good morning", "good afternoon", "good evening", "sup"],
    "BROWSE": ["what", "have", "products", "catalog", "show", "list", "options", "see", "browse"],
    "SELECT": ["1", "2", "3", "4", "5", "6", "7", "8", "9"],
    "QUANTITY": [],
    "CHECKOUT": ["buy", "checkout", "proceed", "go ahead"],
    "CONFIRM": ["confirm", "yes", "yeah", "sure", "ok", "okay"],
    "PAID": ["paid", "i paid", "transferred", "sent", "payment done"],
    "CANCEL": ["cancel", "stop", "no", "never mind", "nah"],
    "TRACK": ["where", "track", "status", "delivery", "shipped", "order status"],
    "HANDOFF": ["speak to", "talk to", "human", "agent", "help me", "manager", "owner"],
    "MENU": ["menu", "0", "back", "restart", "start over", "home"],
    "QUESTION": ["question", "ask", "enquiry", "info"],
}


def classify_intent(message: str, current_state: str) -> Intent:
    m = message.strip().lower()

    # Button IDs get instant routing
    if m == "buy_now":
        return "CHECKOUT"
    if m == "ask_question":
        return "QUESTION"
    if m == "back_to_catalog":
        return "BROWSE"
    if m == "confirm_order":
        return "CONFIRM"
    if m == "cancel_order":
        return "CANCEL"
    if m == "paid":
        return "PAID"
    if m == "menu":
        return "MENU"
    if m == "track":
        return "TRACK"
    if m == "help":
        return "HANDOFF"
    if m == "onboard_yes":
        return "CONFIRM"
    if m == "onboard_no":
        return "CANCEL"

    # Global
    if m in ("menu", "0", "back"):
        return "MENU"

    # State-aware
    if current_state == "browse" and m.isdigit():
        return "SELECT"
    if current_state == "select" and m == "buy_now":
        return "CHECKOUT"
    if current_state == "select" and m == "ask_question":
        return "QUESTION"
    if current_state == "select" and m == "back_to_catalog":
        return "BROWSE"
    if current_state == "cart" and m.isdigit():
        return "QUANTITY"
    if current_state in ("confirm",) and any(p in m for p in PATTERNS["PAID"]):
        return "PAID"
    if current_state == "summary" and any(p in m for p in PATTERNS["CONFIRM"]):
        return "CONFIRM"

    # Pattern matching
    for intent, patterns in PATTERNS.items():
        if any(p in m for p in patterns):
            return intent  # type: ignore

    if m.isdigit():
        return "SELECT"
    return "UNKNOWN"
