SCRIPTS = {
    "buyer": {
        "welcome": lambda shop_name, location: (
            f"Hey! Welcome to *{shop_name}* \U0001F44B\n\n"
            f"We're a{'n online' if not location else ''} shop"
            f"{' based in ' + location if location else ''}.\n"
            "Check out what we have below!"
        ),
        "catalog_intro": lambda shop_name: f"*{shop_name}*\nPick a product:",
        "product_detail": lambda name, price, stock: (
            f"*{name}*\n\u20a6{price:,} | {stock} in stock"
        ),
        "qty_prompt": lambda max_stock: f"How many? (1-{max_stock})",
        "cart_summary": lambda qty, name, price, subtotal: (
            f"\u2714 {qty}x {name} \u20a6{subtotal:,}"
        ),
        "address_prompt": lambda: "Delivery address?",
        "payment_details": lambda shop, bank, acct, total: (
            f"\U0001F4B3 Pay \u20a6{total:,}\n"
            f"*{shop}*\n{bank}\n`{acct}`\n\n"
            "Transferred? Tap below."
        ),
        "paid_checking": lambda: "\u23F3 Checking payment...",
        "paid_confirmed": lambda order_num: f"\u2705 Order *#{order_num}* confirmed!",
        "CONFIRM_RECEIVED": lambda order_num: f"\u2705 Payment confirmed for *#{order_num}*!",
        "cancelled": lambda: "Order cancelled.",
        "invalid": lambda: "Try again or tap MENU.",
        "out_of_stock": lambda left: f"Only {left} left. How many?",
        "handoff": lambda name: f"Connecting you to *{name}*...",
        "track_none": lambda: "No orders yet. Reply MENU to shop!",
        "track_status": lambda num, status: f"*#{num}* — {status.upper()}",
        "shop_empty": lambda name: f"*{name}*\nCatalog coming soon!",
    },
    "seller": {
        "menu": lambda shop_name: f"*{shop_name}*",
        "new_order": lambda num, total, phone, addr: (
            f"\U0001F4E6 *#{num}* \u20a6{total:,}\n{phone}\n{addr}"
        ),
        "balance": lambda avail, pending: (
            f"\U0001F4B0 \u20a6{avail:,} available\n\u23F3 \u20a6{pending:,} pending"
        ),
        "order_list": lambda orders: (
            "No orders." if not orders else
            "\n".join(f'*#{o["order_number"]}* \u20a6{o["total_kobo"]//100:,} {o["status"]}' for o in orders)
        ),
        "pause": lambda: "\u23F8 Bot paused. RESUME to restart.",
        "resume": lambda: "\u25B6 Bot live!",
        "echo_pause": lambda buyer: f"\u23F8 Chatting with *{buyer}*. RESUME when done.",
        "onboard_welcome": lambda: (
            "Welcome to *Hustaq*! \U0001F389\n\n"
            "I help you sell on WhatsApp.\n"
            "I answer your buyers, take orders, and confirm payments — so you don't have to.\n\n"
            "Ready to set up your shop?"
        ),
        "onboard_shopname": lambda: "What's your shop called?\n(e.g. Amina Fabrics)",
        "onboard_category": lambda: "What do you sell?\n\n1. Fashion\n2. Food & Drinks\n3. Beauty\n4. Gadgets\n5. Other",
        "onboard_location": lambda: "Where are you based?\n(e.g. Yaba, Lagos)",
        "onboard_done": lambda shop: (
            f"\u2705 *{shop}* is now live!\n\n"
            "Here's what I can do for you:\n"
            "\u2022 Answer buyer questions\n"
            "\u2022 Take orders automatically\n"
            "\u2022 Confirm payments\n\n"
            "Send a product photo to add your first item!"
        ),
        "product_photo": lambda: "Photo received. Product name?",
        "product_name": lambda: "Price? (Naira, numbers only)",
        "product_saved": lambda name, price: f"\u2705 *{name}* \u20a6{price:,} added!",
        "invalid_price": lambda: "Enter a valid price (e.g. 8500)",
        "unknown": lambda shop: f"Reply MENU for options.",
        "payment_ready": lambda shop, bank, acct: f"\u2705 Pay to: *{shop}* {bank} `{acct}`",
    }
}
