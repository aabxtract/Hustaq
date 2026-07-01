from typing import Literal

Intent = Literal[
    "BROWSE", "SELECT", "QUANTITY", "CHECKOUT", "CONFIRM",
    "CANCEL", "GREETING", "HANDOFF", "TRACK", "PAID", "UNKNOWN"
]

PATTERNS: dict[str, list[str]] = {
    "GREETING": ["hi", "hello", "hey", "good morning", "good afternoon", "good evening", "oya", "sup"],
    "BROWSE": ["what", "have", "products", "catalog", "show", "list", "menu", "options", "items", "see"],
    "SELECT": ["1", "2", "3", "4", "5", "first", "second", "third", "that one", "this one"],
    "QUANTITY": ["how many", "give me", "i want", "send me", "order", "yards", "pieces", "units", "bags"],
    "CHECKOUT": ["buy", "checkout", "proceed", "done", "go ahead"],
    "CONFIRM": ["confirm"],
    "PAID": ["paid", "i paid", "i have paid", "transferred", "sent", "done"],
    "CANCEL": ["cancel", "stop", "no", "never mind", "change mind", "nope"],
    "TRACK": ["where", "track", "status", "delivery", "shipped", "when", "update"],
    "HANDOFF": ["speak to", "talk to", "call", "human", "agent", "real person", "manager", "owner"],
}

def classify_intent(message: str, current_state: str) -> Intent:
    m = message.strip().lower()
    if current_state == "browse" and m.isdigit():
        return "SELECT"
    if current_state == "select" and m == "1":
        return "CHECKOUT"
    if current_state == "cart" and m.isdigit():
        return "QUANTITY"
    if current_state == "confirm" and any(p in m for p in PATTERNS["PAID"]):
        return "PAID"
    for intent, patterns in PATTERNS.items():
        if any(p in m for p in patterns):
            return intent  # type: ignore
    return "UNKNOWN"
