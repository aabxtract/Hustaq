import httpx
from src.lib.config import get_settings
from src.lib.redis_client import get_redis

SANDBOX_URL = "https://sandbox.nomba.com"
PROD_URL = "https://api.nomba.com"


def _base_url() -> str:
    settings = get_settings()
    return SANDBOX_URL if settings.NOMBA_ENV == "sandbox" else PROD_URL


def _account_id() -> str:
    return get_settings().NOMBA_ACCOUNT_ID


def _request_headers(token: str | None = None) -> dict:
    headers = {
        "Content-Type": "application/json",
        "accountId": _account_id(),
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


async def get_nomba_token() -> str:
    """Get cached Nomba access token, or fetch a new one."""
    r = get_redis()
    cached = r.get("nomba:token")
    if cached:
        return cached

    settings = get_settings()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{_base_url()}/v1/auth/token/issue",
            headers=_request_headers(),
            json={
                "grant_type": "client_credentials",
                "client_id": settings.NOMBA_CLIENT_ID,
                "client_secret": settings.NOMBA_CLIENT_SECRET,
            },
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        token = data["access_token"]
        r.setex("nomba:token", 3500, token)
        return token


async def create_virtual_account(seller_id, shop_name: str, callback_url: str) -> dict:
    """Create a Nomba virtual account for a seller."""
    token = await get_nomba_token()

    account_ref = f"hustaq-seller-{seller_id}"
    if len(account_ref) < 16:
        account_ref = account_ref.ljust(16, "0")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{_base_url()}/v1/accounts/virtual",
            headers=_request_headers(token),
            json={
                "accountRef": account_ref,
                "accountName": shop_name,
                "currency": "NGN",
                "callbackUrl": callback_url,
            },
        )
        resp.raise_for_status()
        data = resp.json()["data"]

    return {
        "account_number": data["bankAccountNumber"],
        "bank_name": data["bankName"],
        "bank_code": data.get("bankCode", ""),
        "account_name": data.get("bankAccountName", ""),
        "account_ref": data.get("accountRef", ""),
    }


async def nomba_request(method: str, endpoint: str, **kwargs) -> httpx.Response:
    """Make an authenticated Nomba API request with auto-retry on 401."""
    token = await get_nomba_token()
    headers = kwargs.pop("headers", {})
    headers.setdefault("accountId", _account_id())
    headers["Authorization"] = f"Bearer {token}"

    async with httpx.AsyncClient() as client:
        resp = await client.request(
            method, f"{_base_url()}{endpoint}", headers=headers, **kwargs
        )

    if resp.status_code == 401:
        r = get_redis()
        r.delete("nomba:token")
        token = await get_nomba_token()
        headers["Authorization"] = f"Bearer {token}"
        async with httpx.AsyncClient() as client:
            resp = await client.request(
                method, f"{_base_url()}{endpoint}", headers=headers, **kwargs
            )

    return resp
