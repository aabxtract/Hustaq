SCRIPTS: dict = {
    'buyer': {
        'welcome_directory': lambda shops: (
            'Welcome to Hustaq!\n\nWhich shop would you like to visit?\n\n'
            + '\n'.join(f'{i+1}. {s["shop_name"]} ({s["category"]}) - {s["location"]}'
                        for i, s in enumerate(shops))
            + '\n\nReply a number.'
        ),
        'IDLE_greeting': lambda shop_name, catalog: (
            f'Hi! Welcome to {shop_name}. Here is what we have:\n\n{catalog}\n\n'
            'Reply a number to order!'
        ),
        'BROWSE_catalog': lambda items: '\n'.join(
            f'{i+1}. {p["name"]} - N{p["price_kobo"] // 100:,}'
            for i, p in enumerate(items)
        ),
        'SELECT_product': lambda name, price, stock: (
            f'{name} - N{price:,}\n{stock} in stock.\n\n'
            '1. Buy now\n2. Ask a question\n3. Back to catalog'
        ),
        'CART_quantity': lambda max_stock: f'How many would you like? (Max {max_stock})',
        'CART_summary': lambda qty, price, subtotal: (
            f'{qty} x N{price:,} = N{subtotal:,}\n\nReply CONFIRM to proceed or CANCEL.'
        ),
        'CHECKOUT_address': lambda: (
            'Great! Where should we deliver?\n\nType your full address.'
        ),
        'CONFIRM_payment': lambda shop_name, bank, acct, total: (
            f'Order Summary\nTotal: N{total:,}\n\n'
            f'Pay to:\n{shop_name}\n{bank} - {acct}\n\n'
            'Reply PAID when you have transferred.'
        ),
        'CONFIRM_received': lambda order_num: (
            f'Payment received! Order #{order_num} confirmed.\n'
            'We will notify you when it ships.'
        ),
        'CONFIRM_checking': lambda: 'Checking your payment... one moment.',
        'CANCEL_order': lambda: 'Order cancelled. Reply MENU to start again.',
        'INVALID_input': lambda: 'Sorry, I did not get that. Reply MENU to start over.',
        'HANDOFF_notify': lambda name: f'Connecting you to {name} now.',
        'OUT_OF_STOCK': lambda left: f'Only {left} left in stock. How many would you like?',
        'NO_STOCK': lambda: 'Sorry, this item is out of stock.',
        'MENU': lambda shop_name, catalog: (
            f'{shop_name} - Products:\n\n{catalog}\n\nReply a number to order.'
        ),
    },
    'seller': {
        'menu': lambda shop_name: (
            f'{shop_name} - Hustaq\n\n'
            '1. Add Product\n2. View Orders\n3. Check Balance\n4. Settings\n\n'
            'Reply a number.'
        ),
        'new_order': lambda num, total, phone, addr: (
            f'New order #{num} - N{total:,} - PAID\nBuyer: {phone}\nAddress: {addr}'
        ),
        'balance': lambda avail, pending: (
            f'Available: N{avail:,}\nPending: N{pending:,} (settles in 24h)\n\n'
            'Reply WITHDRAW to transfer.'
        ),
        'order_list': lambda orders: (
            'No orders yet!' if not orders else
            '\n'.join(
                f'{i+1}. #{o["order_number"]} N{o["total_kobo"] // 100:,} {o["status"].upper()}'
                for i, o in enumerate(orders)
            )
        ),
        'pause_confirmed': lambda: 'Bot paused. Reply RESUME when done.',
        'resume_confirmed': lambda: 'Bot is back on. I will handle buyers for you.',
        'echo_pause': lambda buyer: (
            f'You are now chatting with a buyer ({buyer}). Bot paused.\nReply RESUME when done.'
        ),
        'onboarding_welcome': lambda: (
            'Welcome to Hustaq! I will answer buyers, take orders, and confirm payments.\n\n'
            'Ready to set up your shop? Reply YES to continue.'
        ),
        'onboarding_shopname': lambda: 'What is your shop name?',
        'onboarding_category': lambda: (
            'What do you sell?\n\n'
            '1. Fashion\n2. Food and Drinks\n3. Beauty\n4. Gadgets\n5. Other'
        ),
        'onboarding_location': lambda: 'Where are you based? (e.g. Yaba Lagos)',
        'onboarding_done': lambda shop: (
            f'Your shop "{shop}" is live on Hustaq!\n\n'
            'Send a photo to add your first product.\n\n'
            'Buyers can now find you on Hustaq.'
        ),
        'payment_ready': lambda shop, bank, acct: (
            f'Your payment account is ready.\nBuyers pay to: {shop} - {bank} - {acct}'
        ),
        'product_photo_received': lambda: 'Got the photo! What is the product name?',
        'product_name_received': lambda: 'What is the price in Naira? (numbers only)',
        'product_saved': lambda name, price: (
            f'Product added!\n{name} - N{price:,}\n\n'
            'Send another photo to add more, or reply MENU.'
        ),
        'invalid_price': lambda: 'Please enter a valid price in Naira (numbers only, e.g. 8500)',
        'unknown': lambda shop_name: (
            f'I did not understand that.\n\nReply MENU to see your {shop_name} options.'
        ),
    },
}
