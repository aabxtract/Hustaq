import os
import httpx
from src.lib.redis_client import get_redis
from src.lib.secrets import get_secret

SANDBOX_URL = 'https://api.sandbox.nomba.com/v1'
PROD_URL = 'https://api.nomba.com/v1'


def _base_url() -> str:
    return SANDBOX_URL if os.environ.get('NOMBA_ENV', 'sandbox') == 'sandbox' else PROD_URL


async def get_nomba_token() -> str:
    r = get_redis()
    cached = r.get('nomba:token')
    if cached:
        return cached

    client_id = get_secret('hustaq/nomba/client_id')
    client_secret = get_secret('hustaq/nomba/client_secret')

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f'{_base_url()}/auth/token/issue',
            json={
                'grant_type': 'client_credentials',
                'client_id': client_id,
                'client_secret': client_secret,
            },
        )
        resp.raise_for_status()
        data = resp.json()

    token = data['data']['access_token']
    r.setex('nomba:token', 3500, token)
    return token


async def create_virtual_account(seller_id: str, shop_name: str) -> dict:
    token = await get_nomba_token()
    callback_url = os.environ.get('LAMBDA_URL', '') + '/webhooks/nomba'

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f'{_base_url()}/accounts/virtual',
            headers={'Authorization': f'Bearer {token}'},
            json={
                'accountName': shop_name,
                'currency': 'NGN',
                'accountRef': seller_id,
                'callbackUrl': callback_url,
            },
        )
        resp.raise_for_status()
        data = resp.json()

    return {
        'account_number': data['data']['accountNumber'],
        'bank_name': data['data']['bankName'],
        'bank_code': data['data']['bankCode'],
    }
