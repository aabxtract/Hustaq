import httpx, time
from src.lib.config import settings

_token_cache: dict[str, str | float] = {}

async def get_nomba_token() -> str:
    now = time.time()
    if _token_cache.get("token") and now < _token_cache.get("expires_at", 0):
        return _token_cache["token"]

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://api.sandbox.nomba.com/v1/auth/token/issue",
            json={
                "grant_type": "client_credentials",
                "client_id": settings.NOMBA_CLIENT_ID,
                "client_secret": settings.NOMBA_CLIENT_SECRET,
            },
        )
    data = resp.json()["data"]
    _token_cache["token"] = data["access_token"]
    _token_cache["expires_at"] = now + data.get("expires_in", 3600) - 100
    return _token_cache["token"]

async def create_virtual_account(seller_id, shop_name: str) -> dict:
    token = await get_nomba_token()
    callback_url = f"https://{settings.VERCEL_URL}/api/webhooks/nomba"

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.sandbox.nomba.com/v1/accounts/virtual",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "accountName": shop_name,
                "currency": "NGN",
                "accountRef": str(seller_id),
                "callbackUrl": callback_url,
            },
        )
    data = resp.json()["data"]
    return {
        "account_number": data["accountNumber"],
        "bank_name": data["bankName"],
        "bank_code": data["bankCode"],
    }
