import httpx
from src.lib.config import get_settings
from src.lib.redis_client import get_redis

SANDBOX_URL = "https://api.sandbox.nomba.com/v1"
PROD_URL = "https://api.nomba.com/v1"


def _base_url() -> str:
    settings = get_settings()
    return SANDBOX_URL if settings.NOMBA_ENV == "sandbox" else PROD_URL


async def get_nomba_token() -> str:
    r = get_redis()
    cached = r.get("nomba:token")
    if cached:
        return cached

    settings = get_settings()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{_base_url()}/auth/token/issue",
            json={
                "grant_type": "client_credentials",
                "client_id": settings.NOMBA_CLIENT_ID,
                "client_secret": settings.NOMBA_CLIENT_SECRET,
            },
        )
        resp.raise_for_status()
        data = resp.json()

    token = data["data"]["access_token"]
    r.setex("nomba:token", 3500, token)
    return token


async def create_virtual_account(seller_id, shop_name: str) -> dict:
    token = await get_nomba_token()
    settings = get_settings()
    callback_url = f"https://{settings.VERCEL_URL}/api/webhooks/nomba"

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{_base_url()}/accounts/virtual",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "accountName": shop_name,
                "currency": "NGN",
                "accountRef": str(seller_id),
                "callbackUrl": callback_url,
            },
        )
        resp.raise_for_status()
        data = resp.json()

    return {
        "account_number": data["data"]["accountNumber"],
        "bank_name": data["data"]["bankName"],
        "bank_code": data["data"]["bankCode"],
    }
