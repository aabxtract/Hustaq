from fastapi import APIRouter, Request, Response
from src.lib.redis_client import get_redis
from src.db import queries as db
from src.bot.scripts import SCRIPTS
from src.services.twilio_svc import send_message

router = APIRouter()


@router.post('/nomba')
async def nomba_webhook(request: Request):
    body = await request.json()

    event = body.get('event')
    if event != 'payment.success':
        return Response(content='', status_code=200)

    data = body.get('data', {})
    reference = data.get('reference', '')
    order_id = data.get('orderId', '')
    amount_str = data.get('amount', '0')
    customer = data.get('customer', {})
    buyer_phone = customer.get('phone', '')

    r = get_redis()
    idem_key = f'nomba:processed:{reference}'
    if r.get(idem_key):
        return Response(content='', status_code=200)
    r.setex(idem_key, 86400, '1')

    order = db.get_order(order_id)
    if not order:
        return Response(content='', status_code=200)

    amount_kobo = int(float(amount_str) * 100)

    db.mark_order_paid(order_id, reference)
    db.create_payment(order_id, str(order['seller_id']), buyer_phone, amount_kobo, reference)
    db.credit_seller_balance(str(order['seller_id']), amount_kobo)

    from src.lib.db import query
    sellers = query('SELECT * FROM sellers WHERE id = %s', (str(order['seller_id']),))
    seller = sellers[0] if sellers else None

    # Notify buyer
    effective_buyer = buyer_phone or order.get('buyer_phone', '')
    if effective_buyer:
        await send_message(effective_buyer, SCRIPTS['buyer']['CONFIRM_received'](
            order['order_number']
        ))

    # Notify seller
    if seller:
        await send_message(seller['phone_number'], SCRIPTS['seller']['new_order'](
            order['order_number'],
            order['total_kobo'] // 100,
            effective_buyer,
            order.get('delivery_address', ''),
        ))

    return Response(content='', status_code=200)
