import json
import uuid
from src.lib.db import query


# --- Sellers ---

def get_seller_by_twilio_number(twilio_number: str) -> dict | None:
    rows = query('SELECT * FROM sellers WHERE twilio_number = %s', (twilio_number,))
    return rows[0] if rows else None


def get_seller_by_phone(phone: str) -> dict | None:
    rows = query('SELECT * FROM sellers WHERE phone_number = %s', (phone,))
    return rows[0] if rows else None


def get_all_active_sellers() -> list[dict]:
    return query('SELECT * FROM sellers WHERE bot_paused = FALSE ORDER BY created_at')


def upsert_seller_bare(phone: str) -> None:
    slug = f'shop-{phone[-4:]}-{uuid.uuid4().hex[:4]}'
    query(
        '''INSERT INTO sellers (phone_number, shop_name, shop_slug)
           VALUES (%s, %s, %s) ON CONFLICT (phone_number) DO NOTHING''',
        (phone, 'New Shop', slug),
    )


def update_seller_shop_name(phone: str, name: str) -> None:
    slug = name.lower().replace(' ', '-')
    query(
        'UPDATE sellers SET shop_name = %s, shop_slug = %s WHERE phone_number = %s',
        (name, slug, phone),
    )


def update_seller_category(phone: str, category: str) -> None:
    query('UPDATE sellers SET category = %s WHERE phone_number = %s', (category, phone))


def update_seller_location(phone: str, location: str) -> None:
    query('UPDATE sellers SET location = %s WHERE phone_number = %s', (location, phone))


def update_seller_twilio_number(phone: str, twilio_number: str) -> None:
    query('UPDATE sellers SET twilio_number = %s WHERE phone_number = %s', (twilio_number, phone))


def set_bot_paused(seller_id: str, paused: bool) -> None:
    query('UPDATE sellers SET bot_paused = %s WHERE id = %s', (paused, seller_id))


def update_seller_nomba(seller_id: str, account: str, bank_name: str, bank_code: str) -> None:
    query(
        '''UPDATE sellers
           SET nomba_virtual_account = %s, nomba_bank_name = %s, nomba_bank_code = %s
           WHERE id = %s''',
        (account, bank_name, bank_code, seller_id),
    )


def credit_seller_balance(seller_id: str, amount_kobo: int) -> None:
    query(
        'UPDATE sellers SET balance_kobo = balance_kobo + %s WHERE id = %s',
        (amount_kobo, seller_id),
    )


# --- Products ---

def get_products(seller_id: str) -> list[dict]:
    return query(
        'SELECT * FROM products WHERE seller_id = %s AND visible = TRUE ORDER BY created_at',
        (seller_id,),
    )


def create_product(seller_id: str, name: str, price_kobo: int, photo_url: str = '') -> dict:
    rows = query(
        '''INSERT INTO products (seller_id, name, price_kobo, stock_count, photo_url)
           VALUES (%s, %s, %s, 99, %s) RETURNING *''',
        (seller_id, name, price_kobo, photo_url),
    )
    return rows[0]


def decrement_stock(product_id: str, qty: int) -> None:
    query(
        'UPDATE products SET stock_count = stock_count - %s WHERE id = %s AND stock_count >= %s',
        (qty, product_id, qty),
    )


# --- Conversations ---

def get_conversation(seller_wa: str, buyer_phone: str) -> dict | None:
    rows = query(
        'SELECT * FROM conversations WHERE seller_whatsapp_number = %s AND buyer_phone = %s',
        (seller_wa, buyer_phone),
    )
    return rows[0] if rows else None


def create_conversation(seller_id: str, seller_wa: str, buyer_phone: str) -> dict:
    query(
        '''INSERT INTO conversations (seller_id, seller_whatsapp_number, buyer_phone)
           VALUES (%s, %s, %s) ON CONFLICT DO NOTHING''',
        (seller_id, seller_wa, buyer_phone),
    )
    return get_conversation(seller_wa, buyer_phone)


def update_conv_state(conv_id: str, state: str) -> None:
    query(
        'UPDATE conversations SET state = %s, last_message_at = NOW() WHERE id = %s',
        (state, conv_id),
    )


def update_conv_handoff(seller_id: str, active: bool) -> None:
    query(
        'UPDATE conversations SET handoff_active = %s WHERE seller_id = %s',
        (active, seller_id),
    )


def set_pending_order(conv_id: str, order_id: str) -> None:
    query(
        'UPDATE conversations SET pending_order_id = %s WHERE id = %s',
        (order_id, conv_id),
    )


def reset_conversation(conv_id: str) -> None:
    query(
        '''UPDATE conversations
           SET state = %s, pending_order_id = NULL, handoff_active = FALSE, last_message_at = NOW()
           WHERE id = %s''',
        ('idle', conv_id),
    )


# --- Orders ---

def create_order(seller_id: str, buyer_phone: str, items: list,
                 subtotal_kobo: int, total_kobo: int, address: str) -> dict:
    order_number = f'HQ-{uuid.uuid4().hex[:6].upper()}'
    rows = query(
        '''INSERT INTO orders
           (order_number, seller_id, buyer_phone, items, subtotal_kobo, total_kobo, delivery_address)
           VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING *''',
        (order_number, seller_id, buyer_phone,
         json.dumps(items), subtotal_kobo, total_kobo, address),
    )
    return rows[0]


def get_order(order_id: str) -> dict | None:
    rows = query('SELECT * FROM orders WHERE id = %s', (order_id,))
    return rows[0] if rows else None


def get_seller_orders(seller_id: str, limit: int = 5) -> list[dict]:
    return query(
        'SELECT * FROM orders WHERE seller_id = %s ORDER BY created_at DESC LIMIT %s',
        (seller_id, limit),
    )


def mark_order_paid(order_id: str, nomba_reference: str) -> None:
    query(
        '''UPDATE orders SET status = %s, payment_status = %s, nomba_reference = %s
           WHERE id = %s''',
        ('paid', 'paid', nomba_reference, order_id),
    )


# --- Payments ---

def create_payment(order_id: str, seller_id: str, buyer_phone: str,
                   amount_kobo: int, nomba_reference: str) -> None:
    query(
        '''INSERT INTO payments (order_id, seller_id, buyer_phone, amount_kobo, nomba_reference, status)
           VALUES (%s, %s, %s, %s, %s, %s)''',
        (order_id, seller_id, buyer_phone, amount_kobo, nomba_reference, 'success'),
    )
