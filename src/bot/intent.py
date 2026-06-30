from typing import Literal

Intent = Literal[
    'BROWSE', 'SELECT', 'QUANTITY', 'CHECKOUT', 'CONFIRM',
    'CANCEL', 'GREETING', 'HANDOFF', 'TRACK', 'PAID', 'MENU', 'UNKNOWN'
]

PATTERNS: dict[str, list[str]] = {
    'GREETING': ['hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening',
                 'oya', 'sup', 'start', 'begin'],
    'BROWSE':   ['what', 'have', 'products', 'catalog', 'show', 'list', 'options', 'items', 'see'],
    'SELECT':   ['1', '2', '3', '4', '5', 'first', 'second', 'third', 'that one', 'this one'],
    'QUANTITY': ['how many', 'give me', 'i want', 'send me', 'yards', 'pieces', 'units', 'bags'],
    'CHECKOUT': ['buy', 'checkout', 'proceed', 'done', 'go ahead'],
    'CONFIRM':  ['confirm'],
    'PAID':     ['paid', 'i paid', 'i have paid', 'transferred', 'sent'],
    'CANCEL':   ['cancel', 'stop', 'no', 'never mind', 'change mind', 'nope'],
    'TRACK':    ['where', 'track', 'status', 'delivery', 'shipped', 'when', 'update'],
    'HANDOFF':  ['speak to', 'talk to', 'human', 'agent', 'real person', 'manager', 'owner'],
    'MENU':     ['menu', '0', 'back', 'restart', 'start over', 'home'],
}


def classify_intent(message: str, current_state: str) -> Intent:
    m = message.strip().lower()

    # State-aware overrides take priority
    if m in ('menu', '0', 'back'):
        return 'MENU'
    if current_state == 'directory' and m.isdigit():
        return 'SELECT'
    if current_state == 'browse' and m.isdigit():
        return 'SELECT'
    if current_state == 'select' and m == '1':
        return 'CHECKOUT'
    if current_state == 'select' and m == '3':
        return 'BROWSE'
    if current_state == 'cart' and m.isdigit():
        return 'QUANTITY'
    if current_state == 'confirm' and any(p in m for p in PATTERNS['PAID']):
        return 'PAID'

    for intent, patterns in PATTERNS.items():
        if any(p in m for p in patterns):
            return intent  # type: ignore

    # Bare digit in any state is a SELECT attempt
    if m.isdigit():
        return 'SELECT'

    return 'UNKNOWN'
