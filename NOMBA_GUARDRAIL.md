# HUSTAQ — NOMBA GUARDRAIL & CODE REFERENCE

> **Purpose:** This document is your single source of truth for integrating Nomba correctly into Hustaq. Read this before writing any Nomba-related code. It prevents the most common bugs, auth mistakes, and webhook handling errors.

> **Stack:** Python 3.12 · FastAPI · Vercel · Meta WhatsApp Cloud API · Nomba · Upstash Redis · PostgreSQL

---

## Table of Contents

1. [Critical Discovery: Nomba Auth is NOT JWT](#1-critical-discovery-nomba-auth-is-not-jwt)
2. [Your Nomba Credentials — How to Use Them](#2-your-nomba-credentials--how-to-use-them)
3. [Environment URLs](#3-environment-urls)
4. [Authentication: Token Flow](#4-authentication-token-flow)
5. [Virtual Account Creation](#5-virtual-account-creation)
6. [Webhook Handling: payment.success](#6-webhook-handling-paymentsuccess)
7. [Webhook Signature Verification](#7-webhook-signature-verification)
8. [Common Bugs & How to Avoid Them](#8-common-bugs--how-to-avoid-them)
9. [Complete Nomba Service Code](#9-complete-nomba-service-code)
10. [Complete Webhook Handler Code](#10-complete-webhook-handler-code)
11. [Testing Checklist](#11-testing-checklist)

---

## 1. Critical Discovery: Nomba Auth is NOT JWT

**THIS IS THE #1 MISTAKE DEVELOPERS MAKE.**

When Nomba says "Private Key" in your credentials, they do **NOT** mean a cryptographic private key for JWT signing. They mean a **client_secret** in standard OAuth2 `client_credentials` flow.

| What You Might Think | What Nomba Actually Does |
|----------------------|--------------------------|
| "Private key = I need to sign a JWT with RS256" | ❌ WRONG |
| "Private key = client_secret for OAuth2 client_credentials" | ✅ CORRECT |

### The Correct Auth Flow

```
POST https://sandbox.nomba.com/v1/auth/token/issue
Headers:
  Content-Type: application/json
  accountId: f666ef9b-888e-4799-85ce-acb505b28023

Body:
{
  "grant_type": "client_credentials",
  "client_id": "706df6c4-b8bb-4130-88c4-d21b052f8631",
  "client_secret": "k8UobYk3APgOoxUnNL7VpuxzwTsH4LsXtydfjcHs8RH0YISBB4OMqJsaafG+U8fWETu9YZ96bNXE+DelCDuMPw=="
}
```

**Response:**
```json
{
  "code": "00",
  "description": "Success",
  "data": {
    "businessId": "01a10aeb-d989-460a-bbde-9842f2b4320f",
    "access_token": "eyJhbGciOiJIUzI1NiJ9...",
    "refresh_token": "01h4gdx2...",
    "expiresAt": "2026-01-01T12:00:00Z"
  }
}
```

**No JWT signing. No RS256. No `client_assertion`. Just plain OAuth2 client_credentials.**

## 2. Your Nomba Credentials — How to Use Them

### Account Structure

| Account Type | ID | How to Use |
|--------------|-----|------------|
| **Parent Account** | `f666ef9b-888e-4799-85ce-acb505b28023` | Send in EVERY request header as `accountId` |
| **Your Sub-account** | `12ed4167-faa8-49c4-85ef-42f5e8da6780` | Scope your API calls to this account (passed in some endpoints) |

### Credential Sets

| Environment | Client ID | Client Secret | Use For |
|-------------|-----------|---------------|---------|
| **TEST** | `706df6c4-b8bb-4130-88c4-d21b052f8631` | `k8UobYk3APgOoxUnNL7VpuxzwTsH4LsXtydfjcHs8RH0YISBB4OMqJsaafG+U8fWETu9YZ96bNXE+DelCDuMPw==` | Development, hackathon demo |
| **LIVE** | `e5e85b13-f560-4643-814e-c87435dbbc15` | `8/doS7Q3w77EANpk3vpgSrc05hhOiRWp3eBs01sXyZ1AmovtZUXlmrxie+xnEF2tR4q79t0IFufMD1d4JrkT8g==` | Production only |

### Environment Variables

```bash
# Vercel Environment Variables — set ALL of these
NOMBA_CLIENT_ID=706df6c4-b8bb-4130-88c4-d21b052f8631
NOMBA_CLIENT_SECRET=k8UobYk3APgOoxUnNL7VpuxzwTsH4LsXtydfjcHs8RH0YISBB4OMqJsaafG+U8fWETu9YZ96bNXE+DelCDuMPw==
NOMBA_ACCOUNT_ID=f666ef9b-888e-4799-85ce-acb505b28023
NOMBA_SUB_ACCOUNT_ID=12ed4167-faa8-49c4-85ef-42f5e8da6780
NOMBA_ENV=sandbox
NOMBA_WEBHOOK_SECRET=your_webhook_secret_from_dashboard
```

## 3. Environment URLs

| Environment | Base URL | When to Use |
|-------------|----------|-------------|
| **Sandbox** | `https://sandbox.nomba.com` | Development, testing, hackathon |
| **Production** | `https://api.nomba.com` | Live transactions, real money |

**CRITICAL RULE:** Base URL and credentials must ALWAYS match the same environment.
- Sandbox URL + Live credentials = ❌ Authentication error
- Live URL + Sandbox credentials = ❌ Authentication error

**Sandbox checkout endpoints use `/sandbox/checkout/` prefix, not `/v1/checkout/`**

## 4. Authentication: Token Flow

### Token Lifecycle

1. **Request token** using `client_credentials` grant
2. **Cache token** in Redis with TTL slightly less than expiry (e.g., 3500s for 3600s token)
3. **Use token** in `Authorization: Bearer <token>` header for all API calls
4. **Refresh token** when expired or when API returns 401

### Token is Short-Lived

> "The sandbox token is short-lived — if you get `401` errors mid-test, generate a new one."

### Redis Key Pattern

```
nomba:token  ->  "eyJhbGciOiJIUzI1NiJ9..."
TTL: 3500 seconds (token expires in 3600s, refresh 100s early)
```

## 5. Virtual Account Creation

### Endpoint

```
POST /v1/accounts/virtual
```

### Required Headers

```
Authorization: Bearer <access_token>
Content-Type: application/json
accountId: f666ef9b-888e-4799-85ce-acb505b28023
```

### Request Body

```json
{
  "accountRef": "hustaq-seller-12345-uuid",
  "accountName": "Amina Fabrics",
  "currency": "NGN",
  "callbackUrl": "https://your-app.vercel.app/webhooks/nomba"
}
```

| Field | Required | Description | Rules |
|-------|----------|-------------|-------|
| `accountRef` | ✅ Yes | Your internal reference for this account | Length: 16-64 chars. Use seller UUID or phone number. |
| `accountName` | ✅ Yes | Display name for the account | Length: 8-64 chars. Use shop name. |
| `currency` | ✅ Yes | Account currency | Always `"NGN"` for Nigeria |
| `callbackUrl` | ❌ No | Webhook URL for payment notifications | Your Vercel app URL + `/webhooks/nomba` |
| `bvn` | ❌ No | Bank Verification Number | Optional. Can add later for KYC. |
| `expiryDate` | ❌ No | Account expiry | Format: `"2026-01-30 12:15:00"`. ⚠️ Be careful — expired accounts reject payments. |
| `expectedAmount` | ❌ No | Expected payment amount | Optional. Use if you want the account to only receive a specific amount. |

### Response (Success)

```json
{
  "code": "00",
  "description": "Success",
  "data": {
    "createdAt": "2026-07-03T10:00:00.000Z",
    "accountHolderId": "01a10aeb-d989-460a-bbde-9842f2b4320f",
    "accountRef": "hustaq-seller-12345-uuid",
    "accountName": "Amina Fabrics",
    "currency": "NGN",
    "bankName": "Nombank MFB",
    "bankAccountNumber": "9391076543",
    "bankAccountName": "Nomba/Amina Fabrics",
    "callbackUrl": "https://your-app.vercel.app/webhooks/nomba",
    "expired": false
  }
}
```

### What to Store in Your Database

```sql
UPDATE sellers SET
  nomba_virtual_account = '9391076543',
  nomba_bank_name = 'Nombank MFB',
  nomba_bank_code = '090645'
WHERE id = 'seller-uuid';
```

## 6. Webhook Handling: payment.success

### Webhook Payload Structure

```json
{
  "event_type": "payment_success",
  "requestId": "45f2dc2d-d559-4773-bba3-2XXXXXXXXXX",
  "data": {
    "merchant": {
      "walletId": "6756ff80aafe04a795f18b3XXXXXXXXXX",
      "walletBalance": 6052,
      "userId": "b7b10e81-e57d-41d0-8XXXXXXXXXX"
    },
    "terminal": {},
    "transaction": {
      "aliasAccountNumber": "5343270516",
      "fee": 5,
      "sessionId": "IFAP-TRANSFER-46501-...",
      "type": "vact_transfer",
      "transactionId": "API-VACT_TRA-...",
      "aliasAccountName": "Nomba/Amina Fabrics",
      "responseCode": "",
      "originatingFrom": "api",
      "transactionAmount": 1000,
      "narration": "Chijioke Transfer 10.00 To Nomba/Amina Fabrics - Nomba",
      "time": "2026-07-03T10:51:44Z",
      "aliasAccountReference": "hustaq-seller-12345-uuid",
      "aliasAccountType": "VIRTUAL"
    },
    "customer": {
      "bankCode": "090645",
      "senderName": "Chijioke",
      "bankName": "Nombank",
      "accountNumber": "0000000000"
    }
  }
}
```

### Key Fields to Extract

| Path | Field | Use For |
|------|-------|---------|
| `event_type` | Event type | Route to correct handler |
| `data.transaction.aliasAccountReference` | Your `accountRef` | Lookup which seller received payment |
| `data.transaction.transactionAmount` | Amount in kobo | Update seller balance (amount is in NAIRA, multiply by 100 for kobo) |
| `data.transaction.transactionId` | Nomba transaction ID | Idempotency key |
| `data.transaction.time` | Timestamp | Signature verification |
| `data.customer.senderName` | Payer name | Buyer receipt message |

### ⚠️ CRITICAL: Amount is in NAIRA, not Kobo

Nomba sends `transactionAmount` in **Naira** (e.g., `10.00` = ₦10). Your database stores `balance_kobo` in **kobo** (₦10 = 1000 kobo). **Always multiply by 100.**

```python
amount_kobo = int(transaction_amount * 100)  # 10.00 Naira -> 1000 kobo
```

### Idempotency — Prevent Double Processing

```python
# Before processing ANY webhook:
transaction_id = payload['data']['transaction']['transactionId']
redis_key = f'nomba:processed:{transaction_id}'

if redis.get(redis_key):
    return Response(status_code=200)  # Already processed, return 200

# Process payment...
# Then mark as processed:
redis.setex(redis_key, 86400, '1')  # 24 hour TTL
```

### Processing Flow

```
1. Verify webhook signature -> reject if invalid
2. Check idempotency key -> return 200 if already processed
3. Extract transactionId, aliasAccountReference, amount
4. Lookup seller by accountRef
5. Update order status -> 'paid'
6. Update seller balance_kobo += amount * 100
7. Send WhatsApp receipt to buyer
8. Send WhatsApp order alert to seller
9. Set idempotency key in Redis
10. Return 200
```

## 7. Webhook Signature Verification

### How Nomba Signs Webhooks

Nomba generates the signature using:
1. Extract specific fields from the payload
2. Concatenate them with `:` separator
3. Hash with HMAC-SHA256 using your webhook secret
4. Base64 encode the result

### Hashing Payload Construction

```python
event_type = payload['event_type']
request_id = payload['requestId']
user_id = payload['data']['merchant']['userId']
wallet_id = payload['data']['merchant']['walletId']
transaction_id = payload['data']['transaction']['transactionId']
transaction_type = payload['data']['transaction']['type']
transaction_time = payload['data']['transaction']['time']
transaction_response_code = payload['data']['transaction'].get('responseCode', '')
if transaction_response_code == 'null':
    transaction_response_code = ''
timestamp = request.headers.get('nomba-timestamp')

hashing_payload = (
    f"{event_type}:{request_id}:{user_id}:{wallet_id}:"
    f"{transaction_id}:{transaction_type}:{transaction_time}:"
    f"{transaction_response_code}:{timestamp}"
)
```

### Verification Code

```python
import hmac
import hashlib
import base64

def verify_nomba_signature(payload: dict, signature: str, secret: str, timestamp: str) -> bool:
    data = payload.get('data', {})
    merchant = data.get('merchant', {})
    transaction = data.get('transaction', {})

    event_type = payload.get('event_type', '')
    request_id = payload.get('requestId', '')
    user_id = merchant.get('userId', '')
    wallet_id = merchant.get('walletId', '')
    transaction_id = transaction.get('transactionId', '')
    transaction_type = transaction.get('type', '')
    transaction_time = transaction.get('time', '')
    transaction_response_code = transaction.get('responseCode', '')

    if transaction_response_code == 'null':
        transaction_response_code = ''

    hashing_payload = (
        f"{event_type}:{request_id}:{user_id}:{wallet_id}:"
        f"{transaction_id}:{transaction_type}:{transaction_time}:"
        f"{transaction_response_code}:{timestamp}"
    )

    digest = hmac.new(
        secret.encode('utf-8'),
        hashing_payload.encode('utf-8'),
        hashlib.sha256
    ).digest()
    expected_signature = base64.b64encode(digest).decode('utf-8')

    return hmac.compare_digest(expected_signature.lower(), signature.lower())
```

## 8. Common Bugs & How to Avoid Them

### Bug #1: Using JWT for Auth

```python
# ❌ WRONG — Do NOT do this
token = jwt.encode(payload, private_key, algorithm='RS256')

# ✅ CORRECT — Simple OAuth2 client_credentials
resp = httpx.post(
    'https://sandbox.nomba.com/v1/auth/token/issue',
    headers={'accountId': NOMBA_ACCOUNT_ID},
    json={
        'grant_type': 'client_credentials',
        'client_id': NOMBA_CLIENT_ID,
        'client_secret': NOMBA_CLIENT_SECRET
    }
)
```

### Bug #2: Wrong Base URL + Credentials Mismatch

```python
# ❌ WRONG — Sandbox URL with live credentials
url = 'https://sandbox.nomba.com/v1/auth/token/issue'
client_id = LIVE_CLIENT_ID  # Will fail!

# ❌ WRONG — Live URL with sandbox credentials
url = 'https://api.nomba.com/v1/auth/token/issue'
client_id = TEST_CLIENT_ID  # Will fail!

# ✅ CORRECT — Always pair them
if os.environ['NOMBA_ENV'] == 'sandbox':
    base_url = 'https://sandbox.nomba.com'
    client_id = TEST_CLIENT_ID
    client_secret = TEST_CLIENT_SECRET
else:
    base_url = 'https://api.nomba.com'
    client_id = LIVE_CLIENT_ID
    client_secret = LIVE_CLIENT_SECRET
```

### Bug #3: Forgetting accountId Header

```python
# ❌ WRONG — Missing accountId header
headers = {'Authorization': f'Bearer {token}'}

# ✅ CORRECT — accountId is REQUIRED on every request
headers = {
    'Authorization': f'Bearer {token}',
    'accountId': os.environ['NOMBA_ACCOUNT_ID']
}
```

### Bug #4: Not Caching the Token

```python
# ❌ WRONG — Requesting a new token for EVERY API call
# This hits rate limits and slows your app

# ✅ CORRECT — Cache in Redis, refresh before expiry
def get_nomba_token() -> str:
    cached = redis.get('nomba:token')
    if cached:
        return cached
    # ... fetch new token ...
    redis.setex('nomba:token', 3500, new_token)
    return new_token
```

### Bug #5: Not Verifying Webhook Signatures

```python
# ❌ WRONG — Trusting any POST to /webhooks/nomba
@app.post('/webhooks/nomba')
async def nomba_webhook(request: Request):
    data = await request.json()  # Anyone can forge this!
    process_payment(data)

# ✅ CORRECT — Verify signature first
@app.post('/webhooks/nomba')
async def nomba_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get('nomba-signature', '')
    timestamp = request.headers.get('nomba-timestamp', '')
    
    if not verify_nomba_signature(body, signature, WEBHOOK_SECRET, timestamp):
        return Response(status_code=403)
    
    process_payment(await request.json())
```

### Bug #6: Double Processing Payments

```python
# ❌ WRONG — No idempotency check
@app.post('/webhooks/nomba')
async def nomba_webhook(request: Request):
    data = await request.json()
    update_order(data)  # If Nomba retries, order gets updated twice!

# ✅ CORRECT — Redis idempotency key
@app.post('/webhooks/nomba')
async def nomba_webhook(request: Request):
    data = await request.json()
    tx_id = data['data']['transaction']['transactionId']
    
    if redis.get(f'nomba:processed:{tx_id}'):
        return Response(status_code=200)  # Already handled
    
    update_order(data)
    redis.setex(f'nomba:processed:{tx_id}', 86400, '1')
    return Response(status_code=200)
```

### Bug #7: Wrong Amount Unit

```python
# ❌ WRONG — Storing Naira as kobo directly
balance_kobo = transaction_amount  # 10.00 stored as 10 kobo = ₦0.10

# ✅ CORRECT — Convert Naira to kobo
balance_kobo = int(transaction_amount * 100)  # 10.00 -> 1000 kobo = ₦10.00
```

### Bug #8: Not Handling Token Expiry

```python
# ❌ WRONG — Using cached token after expiry
resp = httpx.post(url, headers={'Authorization': f'Bearer {cached_token}'})
# Returns 401, but you don't handle it

# ✅ CORRECT — Auto-refresh on 401
async def nomba_request(method: str, endpoint: str, **kwargs):
    token = get_nomba_token()
    headers = kwargs.pop('headers', {})
    headers['Authorization'] = f'Bearer {token}'
    
    resp = await httpx.request(method, f'{BASE_URL}{endpoint}', headers=headers, **kwargs)
    
    if resp.status_code == 401:
        redis.delete('nomba:token')
        token = get_nomba_token()
        headers['Authorization'] = f'Bearer {token}'
        resp = await httpx.request(method, f'{BASE_URL}{endpoint}', headers=headers, **kwargs)
    
    return resp
```

## 9. Complete Nomba Service Code

```python
# api/services/nomba.py
import os
import httpx
from api.lib.redis_client import redis

BASE_URL = 'https://sandbox.nomba.com' if os.environ.get('NOMBA_ENV') == 'sandbox' else 'https://api.nomba.com'
ACCOUNT_ID = os.environ['NOMBA_ACCOUNT_ID']
CLIENT_ID = os.environ['NOMBA_CLIENT_ID']
CLIENT_SECRET = os.environ['NOMBA_CLIENT_SECRET']


async def get_nomba_token() -> str:
    """Get cached Nomba access token, or fetch a new one."""
    cached = redis.get('nomba:token')
    if cached:
        return cached
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f'{BASE_URL}/v1/auth/token/issue',
            headers={
                'Content-Type': 'application/json',
                'accountId': ACCOUNT_ID
            },
            json={
                'grant_type': 'client_credentials',
                'client_id': CLIENT_ID,
                'client_secret': CLIENT_SECRET
            }
        )
        resp.raise_for_status()
        data = resp.json()['data']
        token = data['access_token']
        
        # Cache for 3500s (token expires at 3600s)
        redis.setex('nomba:token', 3500, token)
        return token


async def create_virtual_account(seller_id: str, shop_name: str, callback_url: str) -> dict:
    """Create a Nomba virtual account for a seller."""
    token = await get_nomba_token()
    
    # accountRef must be 16-64 chars
    account_ref = f'hustaq-seller-{seller_id}'
    if len(account_ref) < 16:
        account_ref = account_ref.ljust(16, '0')
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f'{BASE_URL}/v1/accounts/virtual',
            headers={
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
                'accountId': ACCOUNT_ID
            },
            json={
                'accountRef': account_ref,
                'accountName': shop_name,
                'currency': 'NGN',
                'callbackUrl': callback_url
            }
        )
        resp.raise_for_status()
        return resp.json()['data']


async def nomba_request(method: str, endpoint: str, **kwargs) -> httpx.Response:
    """Make an authenticated Nomba API request with auto-retry on 401."""
    token = await get_nomba_token()
    headers = kwargs.pop('headers', {})
    headers['Authorization'] = f'Bearer {token}'
    headers['accountId'] = ACCOUNT_ID
    
    async with httpx.AsyncClient() as client:
        resp = await client.request(method, f'{BASE_URL}{endpoint}', headers=headers, **kwargs)
        
        if resp.status_code == 401:
            redis.delete('nomba:token')
            token = await get_nomba_token()
            headers['Authorization'] = f'Bearer {token}'
            resp = await client.request(method, f'{BASE_URL}{endpoint}', headers=headers, **kwargs)
        
        return resp
```

## 10. Complete Webhook Handler Code

```python
# api/handlers/nomba.py
from fastapi import APIRouter, Request, Response
import os
import hmac
import hashlib
import base64
from api.lib.redis_client import redis
from api.lib.db import query
from api.services.meta import send_message
from api.bot.scripts import SCRIPTS

router = APIRouter()
WEBHOOK_SECRET = os.environ.get('NOMBA_WEBHOOK_SECRET', '')


def verify_nomba_signature(payload: dict, signature: str, secret: str, timestamp: str) -> bool:
    """Verify Nomba webhook HMAC-SHA256 signature."""
    data = payload.get('data', {})
    merchant = data.get('merchant', {})
    transaction = data.get('transaction', {})

    event_type = payload.get('event_type', '')
    request_id = payload.get('requestId', '')
    user_id = merchant.get('userId', '')
    wallet_id = merchant.get('walletId', '')
    transaction_id = transaction.get('transactionId', '')
    transaction_type = transaction.get('type', '')
    transaction_time = transaction.get('time', '')
    transaction_response_code = transaction.get('responseCode', '')

    if transaction_response_code == 'null':
        transaction_response_code = ''

    hashing_payload = (
        f"{event_type}:{request_id}:{user_id}:{wallet_id}:"
        f"{transaction_id}:{transaction_type}:{transaction_time}:"
        f"{transaction_response_code}:{timestamp}"
    )

    digest = hmac.new(
        secret.encode('utf-8'),
        hashing_payload.encode('utf-8'),
        hashlib.sha256
    ).digest()
    expected = base64.b64encode(digest).decode('utf-8')

    return hmac.compare_digest(expected.lower(), signature.lower())


@router.post('/nomba')
async def nomba_webhook(request: Request):
    """Handle Nomba payment webhooks."""
    body = await request.json()
    
    # 1. Verify signature
    signature = request.headers.get('nomba-signature', '')
    timestamp = request.headers.get('nomba-timestamp', '')
    
    if WEBHOOK_SECRET and not verify_nomba_signature(body, signature, WEBHOOK_SECRET, timestamp):
        return Response(status_code=403)
    
    event_type = body.get('event_type')
    
    if event_type == 'payment_success':
        return await handle_payment_success(body)
    
    # Acknowledge other events
    return Response(status_code=200)


async def handle_payment_success(payload: dict):
    """Process a successful payment webhook."""
    data = payload['data']
    transaction = data['transaction']
    
    tx_id = transaction['transactionId']
    account_ref = transaction['aliasAccountReference']
    amount_naira = transaction['transactionAmount']
    amount_kobo = int(amount_naira * 100)
    sender_name = data['customer']['senderName']
    
    # 2. Idempotency check
    if redis.get(f'nomba:processed:{tx_id}'):
        return Response(status_code=200)
    
    # 3. Find seller by accountRef
    sellers = query(
        'SELECT * FROM sellers WHERE nomba_virtual_account IS NOT NULL',
        ()
    )
    # Match by accountRef pattern: hustaq-seller-{seller_id}
    seller = None
    for s in sellers:
        ref = f"hustaq-seller-{s['id']}"
        if len(ref) < 16:
            ref = ref.ljust(16, '0')
        if ref == account_ref:
            seller = s
            break
    
    if not seller:
        return Response(status_code=200)  # Unknown seller, but return 200
    
    # 4. Find pending order for this seller (most recent)
    orders = query(
        "SELECT * FROM orders WHERE seller_id = %s AND status = 'pending' ORDER BY created_at DESC LIMIT 1",
        (seller['id'],)
    )
    
    if not orders:
        return Response(status_code=200)
    
    order = orders[0]
    
    # 5. Update order
    query(
        "UPDATE orders SET status = 'paid', payment_status = 'paid', nomba_reference = %s, updated_at = NOW() WHERE id = %s",
        (tx_id, order['id'])
    )
    
    # 6. Update seller balance
    query(
        'UPDATE sellers SET balance_kobo = balance_kobo + %s WHERE id = %s',
        (amount_kobo, seller['id'])
    )
    
    # 7. Record payment
    query(
        "INSERT INTO payments (order_id, seller_id, buyer_phone, amount_kobo, status, nomba_reference) VALUES (%s, %s, %s, %s, 'success', %s)",
        (order['id'], seller['id'], order['buyer_phone'], amount_kobo, tx_id)
    )
    
    # 8. Send WhatsApp notifications
    await send_message(order['buyer_phone'], SCRIPTS['buyer']['CONFIRM_RECEIVED'](order['order_number']))
    await send_message(
        seller['phone_number'],
        SCRIPTS['seller']['NEW_ORDER'](
            order['order_number'],
            amount_kobo // 100,
            order['buyer_phone'],
            order['delivery_address']
        )
    )
    
    # 9. Mark as processed
    redis.setex(f'nomba:processed:{tx_id}', 86400, '1')
    
    return Response(status_code=200)
```

## 11. Testing Checklist

### Before You Write Any Nomba Code

- [ ] Confirm `NOMBA_ENV=sandbox` in your Vercel env vars
- [ ] Confirm you are using TEST credentials (not LIVE)
- [ ] Confirm `accountId` header is set on EVERY request
- [ ] Confirm `callbackUrl` is your Vercel app URL + `/webhooks/nomba`

### Auth Testing

- [ ] `curl` the token endpoint — get a valid access_token back
- [ ] Verify token is cached in Upstash Redis under `nomba:token`
- [ ] Wait 3500s, verify token auto-refreshes
- [ ] Verify 401 auto-retry works (force-delete token, make API call)

### Virtual Account Testing

- [ ] Create virtual account via API
- [ ] Verify response contains `bankAccountNumber`, `bankName`, `bankAccountName`
- [ ] Verify seller row in DB is updated
- [ ] Verify `accountRef` is 16-64 chars

### Webhook Testing

- [ ] Send test webhook via `curl` — handler returns 200
- [ ] Verify signature verification blocks forged requests
- [ ] Verify idempotency prevents double processing
- [ ] Verify order status changes to `paid`
- [ ] Verify seller balance increases
- [ ] Verify payment row is created
- [ ] Verify both buyer and seller receive WhatsApp messages

### Integration Testing

- [ ] Complete buyer loop -> order summary shows real Nomba bank details
- [ ] Simulate bank transfer (via Nomba dashboard or curl)
- [ ] Verify webhook fires and updates order
- [ ] Verify both phones get notifications within 2 seconds

---

> **Read this document before writing Nomba code. Re-read it when something breaks. The answer is probably here.**