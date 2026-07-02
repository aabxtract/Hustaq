# HUSTAQ — Meta WhatsApp Cloud API Edition

> WhatsApp-native commerce platform for Nigerian informal sellers.
> **Stack:** Python 3.12 · FastAPI · Vercel · Upstash Redis · PostgreSQL · Meta WhatsApp Cloud API · Nomba Payments

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [What Changed From the Original Guide](#2-what-changed-from-the-original-guide)
3. [Meta WhatsApp Cloud API Setup](#3-meta-whatsapp-cloud-api-setup)
4. [Repository Structure](#4-repository-structure)
5. [Environment Variables](#5-environment-variables)
6. [Phase 1 — Core Buyer Loop (No Nomba)](#6-phase-1--core-buyer-loop-no-nomba)
7. [Phase 2 — Nomba Integration](#7-phase-2--nomba-integration)
8. [Phase 3 — Seller Onboarding & Commands](#8-phase-3--seller-onboarding--commands)
9. [Database Schema](#9-database-schema)
10. [Code Reference](#10-code-reference)
11. [Build Order & Checklist](#11-build-order--checklist)
12. [Demo Day Script](#12-demo-day-script)

---

## 1. Architecture Overview

```
Buyer WhatsApp Message
        |
        v
Meta WhatsApp Cloud API
        |
        | POST webhook (JSON)
        v
Vercel Serverless Function (FastAPI)
        |
        +-----> PostgreSQL (Neon/Supabase/RDS) — persistent data
        |
        +-----> Upstash Redis — conversation state, Nomba token cache
        |
        +-----> S3 / R2 — product photos
        |
        +-----> Nomba API — virtual accounts, payments
        |
        v
Meta WhatsApp Cloud API — sends reply back to buyer/seller
```

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Runtime** | Vercel Serverless Functions (Python 3.12) | FastAPI app, auto-scaling, zero infra management |
| **Web Framework** | FastAPI | Routing, request parsing, async handlers |
| **WhatsApp** | Meta WhatsApp Cloud API | Official API. Webhooks + message sends. |
| **Database** | PostgreSQL (Neon recommended) | 5 tables: sellers, products, orders, conversations, payments |
| **Cache** | Upstash Redis | Conversation state, cart data, Nomba token cache, idempotency |
| **File Storage** | Cloudflare R2 or S3 | Product photos |
| **Payments** | Nomba API | Virtual accounts, payment webhooks |
| **Secrets** | Vercel Environment Variables | All API keys, tokens, DB credentials |

---

## 2. What Changed From the Original Guide

| Original (AWS/Twilio) | New (Vercel/Meta) | Notes |
|-----------------------|-------------------|-------|
| Twilio WhatsApp Business | **Meta WhatsApp Cloud API** | Official Meta API. Requires business verification but you already have it working. |
| AWS Lambda + Mangum | **Vercel Serverless Functions** | FastAPI runs natively. No adapter needed. |
| ElastiCache Redis | **Upstash Redis** | Serverless Redis over HTTP. No VPC needed. |
| RDS PostgreSQL | **Neon PostgreSQL** (or Supabase) | Serverless Postgres. Free tier available. |
| AWS S3 | **Cloudflare R2** (or S3) | S3-compatible, free egress. |
| AWS Secrets Manager | **Vercel Env Vars** | Built-in, encrypted at rest. |
| `serverless.yml` deploy | **`vercel.json` + Git push** | Auto-deploy on push. |
| Twilio form-encoded webhooks | **Meta JSON webhooks** | Nested JSON: `entry[].changes[].value.messages[]` |
| Twilio signature verification | **Meta signature verification** | SHA-256 HMAC of raw body with app secret |
| `whatsapp:` prefix on numbers | **Bare numbers** | Meta sends `from: "2348051234567"` without prefix |

### Key Meta WhatsApp Differences

**Webhook Verification (GET):**
Meta sends a challenge during setup. You must echo it back.

```python
@app.get('/webhook')
async def verify_webhook(request: Request):
    token = request.query_params.get('hub.verify_token')
    challenge = request.query_params.get('hub.challenge')
    if token == os.environ['WEBHOOK_VERIFY_TOKEN']:
        return int(challenge)  # Echo the challenge
    return Response(status_code=403)
```

**Incoming Message Format (POST):**
```json
{
  "object": "whatsapp_business_account",
  "entry": [{
    "changes": [{
      "value": {
        "messages": [{
          "from": "2348051234567",
          "id": "wamid.XXX",
          "timestamp": "1234567890",
          "type": "text",
          "text": { "body": "Hi, do you have Ankara?" }
        }]
      }
    }]
  }]
}
```

**Sending Messages:**
```python
import httpx

async def send_message(to: str, body: str):
    async with httpx.AsyncClient() as client:
        await client.post(
            f'https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/messages',
            headers={'Authorization': f'Bearer {ACCESS_TOKEN}'},
            json={
                'messaging_product': 'whatsapp',
                'to': to,
                'type': 'text',
                'text': {'body': body}
            }
        )
```

---

## 3. Meta WhatsApp Cloud API Setup

### Credentials You Need From Meta Business Manager

| Credential | Where to Find | Store In |
|------------|---------------|----------|
| **Access Token** | Meta Developer Console → Your App → WhatsApp → API Setup | Vercel env var: `META_ACCESS_TOKEN` |
| **Phone Number ID** | Meta Developer Console → WhatsApp → API Setup | Vercel env var: `META_PHONE_NUMBER_ID` |
| **App Secret** | Meta Developer Console → App Settings → Basic | Vercel env var: `META_APP_SECRET` |
| **Webhook Verify Token** | You create this yourself (any random string) | Vercel env var: `WEBHOOK_VERIFY_TOKEN` |

### Webhook Configuration in Meta Developer Console

1. Go to Meta Developer Console → Your App → WhatsApp → Configuration
2. Under **Webhook**, click **Edit**
3. Set **Callback URL** to: `https://your-app.vercel.app/webhook`
4. Set **Verify Token** to match your `WEBHOOK_VERIFY_TOKEN` env var
5. Click **Verify and Save**
6. Under **Webhook Fields**, subscribe to: `messages`

### Testing in Meta Sandbox

Before going live, test with Meta test numbers:
1. Meta Developer Console → WhatsApp → API Setup
2. Add a test phone number
3. Send messages to that number — they will appear in your webhook

---

## 4. Repository Structure

```
hustaq/
├── api/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app entry point
│   ├── handlers/
│   │   ├── meta.py             # Meta webhook receiver (GET verify + POST messages)
│   │   └── nomba.py            # Nomba payment webhook receiver
│   ├── services/
│   │   ├── meta.py             # send_message(), download_media()
│   │   ├── nomba.py            # get_token(), create_virtual_account()
│   │   └── state.py            # process_message() — full state machine
│   ├── bot/
│   │   ├── scripts.py          # SCRIPTS dict — every message string
│   │   ├── intent.py           # classify_intent(message, state) -> Intent
│   │   └── onboarding.py       # Seller onboarding conversation flow
│   ├── db/
│   │   ├── schema.sql          # Full 5-table PostgreSQL schema
│   │   └── queries.py          # All DB read/write functions
│   └── lib/
│       ├── redis_client.py     # Upstash Redis connection
│       └── db.py               # PostgreSQL connection (asyncpg or psycopg2)
│
├── docs/
│   ├── STATE_TRANSITIONS.md    # Every state, intent, script key
│   └── DEMO_SCRIPT.md          # Exact messages to type on demo day
│
├── requirements.txt
├── vercel.json
└── README.md
```

### Vercel Configuration

```json
// vercel.json
{
  "builds": [
    {
      "src": "api/main.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "api/main.py"
    }
  ]
}
```

```python
# api/main.py
from fastapi import FastAPI
from api.handlers.meta import router as meta_router
from api.handlers.nomba import router as nomba_router

app = FastAPI()
app.include_router(meta_router, prefix='/webhook')
app.include_router(nomba_router, prefix='/webhooks')

# Vercel auto-detects the `app` variable
```

---

## 5. Environment Variables

Set these in your Vercel Dashboard → Project Settings → Environment Variables

| Variable | Required For | Value / Notes |
|----------|--------------|---------------|
| `META_ACCESS_TOKEN` | Meta API | From Meta Developer Console |
| `META_PHONE_NUMBER_ID` | Meta API | From Meta Developer Console |
| `META_APP_SECRET` | Webhook verification | From Meta Developer Console |
| `WEBHOOK_VERIFY_TOKEN` | Webhook verification | Any random string you create |
| `DATABASE_URL` | PostgreSQL | Neon/Supabase connection string |
| `UPSTASH_REDIS_REST_URL` | Upstash Redis | From Upstash Console |
| `UPSTASH_REDIS_REST_TOKEN` | Upstash Redis | From Upstash Console |
| `R2_BUCKET` | File storage | Cloudflare R2 bucket name |
| `R2_ACCESS_KEY_ID` | File storage | R2 credentials |
| `R2_SECRET_ACCESS_KEY` | File storage | R2 credentials |
| `R2_ENDPOINT` | File storage | `https://ACCOUNT_ID.r2.cloudflarestorage.com` |
| `NOMBA_CLIENT_ID` | Nomba API | TEST: `706df6c4-b8bb-4130-88c4-d21b052f8631` |
| `NOMBA_CLIENT_SECRET` | Nomba API | TEST private key |
| `NOMBA_ACCOUNT_ID` | Nomba API | `f666ef9b-888e-4799-85ce-acb505b28023` |
| `NOMBA_SUB_ACCOUNT_ID` | Nomba API | `12ed4167-faa8-49c4-85ef-42f5e8da6780` |
| `NOMBA_ENV` | Nomba API | `sandbox` for dev, `live` for production |
| `NOMBA_WEBHOOK_SECRET` | Nomba webhooks | For verifying Nomba webhook signatures |

---

## 6. Phase 1 — Core Buyer Loop (No Nomba)

**Goal:** Buyer messages your WhatsApp number → sees catalog → selects product → confirms quantity → gives address → receives order summary with **static bank placeholder**. Order saved in DB.

### Build Order:

1. **Webhook receiver** (`api/handlers/meta.py`)
   - GET `/webhook` — verify with Meta challenge
   - POST `/webhook` — parse incoming message JSON, extract `from`, `text.body`
   - Verify Meta signature using `META_APP_SECRET`

2. **Send service** (`api/services/meta.py`)
   - `send_message(to, body)` — POST to Meta Graph API
   - `download_media(media_id)` — fetch image from Meta CDN

3. **Database layer** (`api/lib/db.py` + `api/db/schema.sql`)
   - Connect to PostgreSQL (Neon)
   - Run schema.sql (5 tables)
   - Seed demo seller + demo product

4. **Redis layer** (`api/lib/redis_client.py`)
   - Connect to Upstash Redis over REST
   - Helper functions: `get_json(key)`, `set_json(key, value, ttl)`

5. **Bot scripts** (`api/bot/scripts.py`)
   - All buyer + seller message templates as lambda functions

6. **Intent classifier** (`api/bot/intent.py`)
   - `classify_intent(message, current_state)` → Intent
   - State-aware overrides (bare number means different things in different states)

7. **State machine** (`api/services/state.py`)
   - `process_message(from_phone, to_phone, text, media_url)`
   - States: `idle → browse → select → cart → checkout → delivery → confirm`
   - Each handler: read state → validate intent → update DB → send reply → transition state

8. **Test end-to-end**
   - Message your bot → receive catalog → select → quantity → address → static bank details
   - Verify order row in DB with status `pending`

**Phase 1 Exit Condition:** Full buyer conversation works. Order in DB. `git tag v0.1-buyer-loop`

---

## 7. Phase 2 — Nomba Integration

**Goal:** Replace static bank placeholder with real Nomba virtual account. Handle payment webhooks.

### Build Order:

1. **Nomba token service** (`api/services/nomba.py`)
   - `get_nomba_token()` — JWT auth with private key, cache in Redis 3500s
   - **Note:** Nomba uses JWT signing, not simple OAuth. You will sign a JWT with the private key they gave you.

2. **Virtual account creation** (`api/services/nomba.py`)
   - `create_virtual_account(seller_id, shop_name)`
   - POST `/accounts/virtual` with `accountName`, `currency=NGN`, `accountRef=seller_id`
   - On success: update sellers table with `nomba_virtual_account`, `nomba_bank_name`, `nomba_bank_code`

3. **Inject real bank details**
   - In `handle_delivery()`: fetch seller's Nomba details from DB
   - Pass to `SCRIPTS['buyer']['CONFIRM_payment']()`

4. **Nomba webhook handler** (`api/handlers/nomba.py`)
   - POST `/webhooks/nomba` — handle `payment.success`
   - Redis idempotency: `nomba:processed:{reference}`
   - Update order status → `paid`, update seller balance
   - Send receipt to buyer, new order alert to seller

5. **Test**
   - Complete buyer loop with real bank details
   - Curl-test Nomba webhook
   - Verify both phones get notifications

**Phase 2 Exit Condition:** Payment flow works end-to-end. `git tag v0.2-nomba-working`

---

## 8. Phase 3 — Seller Onboarding & Commands

**Goal:** Sellers can text your bot number to create a shop, add products, view orders, check balance, pause/resume bot.

### Why This Comes Last

The original guide had onboarding as part of Phase 1, but your agent focused on the buyer loop first. That is actually fine for a hackathon because:

1. **The buyer loop is the demo** — judges see the buyer experience
2. **You can pre-seed a demo seller** — no need for live onboarding in the demo
3. **Onboarding is a "nice to have" for the pitch** — you can describe it without demoing it

### But You Should Build It Because:

- It makes the platform real (not just a demo)
- It shows you understand both sides of the marketplace
- It unlocks the full Nomba flow (virtual account creation happens during onboarding)

### Build Order:

1. **Seller command router** (`api/services/seller_commands.py`)
   - When message `to` == your bot number → route to seller commands
   - MENU, VIEW ORDERS, CHECK BALANCE, PAUSE, RESUME

2. **Onboarding conversation** (`api/bot/onboarding.py`)
   - Linear flow: WELCOME → SHOP_NAME → CATEGORY → LOCATION → DONE
   - Store onboarding state in Redis: `onboard:{phone}`
   - On DONE: create seller in DB, call `create_virtual_account()`

3. **Product add flow**
   - Seller sends photo → bot asks name → asks price → saves to DB
   - Use `download_media()` to fetch image, upload to R2/S3

4. **Test**
   - Text bot: "I want to sell" → complete onboarding → shop is live
   - Send product photo → name → price → product in DB
   - Text bot: "menu" → see seller dashboard

**Phase 3 Exit Condition:** Seller can onboard and manage shop entirely via WhatsApp. `git tag v0.3-seller-commands`

---

## 9. Database Schema

Same 5-table schema as original guide. Run against your PostgreSQL instance.

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE sellers (
  id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  phone_number              VARCHAR(20) UNIQUE NOT NULL,
  seller_whatsapp_number    VARCHAR(20) UNIQUE,
  -- Meta does not use twilio_number; we match by seller_whatsapp_number or phone_number
  shop_name                 VARCHAR(100) NOT NULL,
  shop_slug                 VARCHAR(100) UNIQUE NOT NULL,
  category                  VARCHAR(50),
  location                  VARCHAR(100),
  bot_paused                BOOLEAN DEFAULT FALSE,
  balance_kobo              BIGINT DEFAULT 0,
  pending_balance_kobo      BIGINT DEFAULT 0,
  nomba_virtual_account     VARCHAR(20),
  nomba_bank_name           VARCHAR(100),
  nomba_bank_code           VARCHAR(10),
  created_at                TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE products (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  seller_id     UUID REFERENCES sellers(id),
  name          VARCHAR(200) NOT NULL,
  price_kobo    BIGINT NOT NULL,
  stock_count   INTEGER DEFAULT 0,
  photo_url     VARCHAR(500),
  visible       BOOLEAN DEFAULT TRUE,
  created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE orders (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_number        VARCHAR(20) UNIQUE,
  seller_id           UUID REFERENCES sellers(id),
  buyer_phone         VARCHAR(20) NOT NULL,
  items               JSONB,
  subtotal_kobo       BIGINT NOT NULL,
  total_kobo          BIGINT NOT NULL,
  status              VARCHAR(20) DEFAULT 'pending',
  payment_status      VARCHAR(20) DEFAULT 'unpaid',
  nomba_reference     VARCHAR(100),
  delivery_address    TEXT,
  created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE conversations (
  id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  seller_id                 UUID REFERENCES sellers(id),
  seller_whatsapp_number    VARCHAR(20) NOT NULL,
  buyer_phone               VARCHAR(20) NOT NULL,
  state                     VARCHAR(20) DEFAULT 'idle',
  cart                      JSONB DEFAULT '{}',
  pending_order_id          UUID REFERENCES orders(id),
  handoff_active            BOOLEAN DEFAULT FALSE,
  last_message_at           TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(seller_whatsapp_number, buyer_phone)
);

CREATE TABLE payments (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id          UUID REFERENCES orders(id),
  seller_id         UUID REFERENCES sellers(id),
  buyer_phone       VARCHAR(20),
  amount_kobo       BIGINT NOT NULL,
  status            VARCHAR(20) DEFAULT 'pending',
  nomba_reference   VARCHAR(100) UNIQUE,
  created_at        TIMESTAMPTZ DEFAULT NOW()
);

-- Seed demo seller (for Phase 1 testing without onboarding)
INSERT INTO sellers (phone_number, shop_name, shop_slug, category, location)
VALUES ('+2348012345678', 'Amina Fabrics', 'amina-fabrics', 'fashion', 'Yaba Lagos');

-- Seed demo product
INSERT INTO products (seller_id, name, price_kobo, stock_count, photo_url)
SELECT id, 'Hollandaise Ankara', 850000, 20, 'https://placehold.co/400'
FROM sellers WHERE shop_slug = 'amina-fabrics';
```

---

## 10. Code Reference

### Upstash Redis Client

```python
# api/lib/redis_client.py
from upstash_redis import Redis
import os, json

redis = Redis(
    url=os.environ['UPSTASH_REDIS_REST_URL'],
    token=os.environ['UPSTASH_REDIS_REST_TOKEN']
)

def get_json(key: str) -> dict | None:
    val = redis.get(key)
    return json.loads(val) if val else None

def set_json(key: str, value: dict, ttl: int = 3600):
    redis.setex(key, ttl, json.dumps(value))
```

### Meta Webhook Handler

```python
# api/handlers/meta.py
from fastapi import APIRouter, Request, Response
import hmac, hashlib, os, json
from api.services.state import process_message
from api.services.seller_commands import handle_seller_command

router = APIRouter()

@router.get('/')
async def verify_webhook(request: Request):
    """Meta sends this during webhook setup"""
    mode = request.query_params.get('hub.mode')
    token = request.query_params.get('hub.verify_token')
    challenge = request.query_params.get('hub.challenge')

    if mode == 'subscribe' and token == os.environ['WEBHOOK_VERIFY_TOKEN']:
        return int(challenge)
    return Response(status_code=403)

@router.post('/')
async def receive_message(request: Request):
    """Handle incoming WhatsApp messages from Meta"""
    body = await request.body()

    # Verify Meta signature
    signature = request.headers.get('X-Hub-Signature-256', '')
    expected = 'sha256=' + hmac.new(
        os.environ['META_APP_SECRET'].encode(),
        body,
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(signature, expected):
        return Response(status_code=403)

    data = await request.json()

    # Extract message
    for entry in data.get('entry', []):
        for change in entry.get('changes', []):
            value = change.get('value', {})
            for message in value.get('messages', []):
                from_phone = message['from']  # "2348051234567"
                text = message.get('text', {}).get('body', '')

                # Route: seller command or buyer state machine
                # (Add routing logic here)
                await process_message(from_phone, text)

    return Response(status_code=200)
```

### Nomba JWT Auth

```python
# api/services/nomba.py
import jwt, time, os, httpx
from api.lib.redis_client import redis

async def get_nomba_token() -> str:
    cached = redis.get('nomba:token')
    if cached:
        return cached

    # Create JWT signed with private key
    now = int(time.time())
    payload = {
        'iss': os.environ['NOMBA_CLIENT_ID'],
        'sub': os.environ['NOMBA_CLIENT_ID'],
        'aud': 'https://api.nomba.com',
        'iat': now,
        'exp': now + 3600
    }

    private_key = os.environ['NOMBA_CLIENT_SECRET']  # The private key they gave you
    token = jwt.encode(payload, private_key, algorithm='RS256')

    # Exchange JWT for access token
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            'https://api.sandbox.nomba.com/v1/auth/token/issue',
            headers={
                'accountId': os.environ['NOMBA_ACCOUNT_ID'],
                'Content-Type': 'application/json'
            },
            json={
                'grant_type': 'client_credentials',
                'client_assertion_type': 'urn:ietf:params:oauth:client-assertion-type:jwt-bearer',
                'client_assertion': token,
                'scope': 'payments'
            }
        )
        data = resp.json()
        access_token = data['data']['access_token']
        redis.setex('nomba:token', 3500, access_token)
        return access_token
```

---

## 11. Build Order & Checklist

### Priority Order (Do This)

| Priority | Task | Phase | Why |
|----------|------|-------|-----|
| **P0** | Meta webhook receives message, logs to console | 1 | Nothing works without this |
| **P0** | `send_message()` sends reply via Meta API | 1 | Verify two-way communication |
| **P0** | Buyer loop: idle→browse→select→cart→checkout→delivery→confirm | 1 | The core demo |
| **P0** | Order saved to DB with static bank placeholder | 1 | Prove persistence |
| **P1** | Nomba token auth working | 2 | Required for virtual accounts |
| **P1** | Virtual account created, real bank details in order summary | 2 | Replace static placeholder |
| **P1** | Nomba webhook handler updates order, sends notifications | 2 | Complete payment flow |
| **P2** | Seller onboarding: WELCOME→SHOP_NAME→CATEGORY→LOCATION→DONE | 3 | Makes platform real |
| **P2** | Seller commands: MENU, VIEW ORDERS, CHECK BALANCE, PAUSE, RESUME | 3 | Seller self-service |
| **P2** | Product add flow: photo→name→price→DB | 3 | Seller inventory mgmt |

### If You Are Short on Time

**Minimum Viable Demo (skip P2):**
1. Pre-seed demo seller + product in DB
2. Build buyer loop with static bank placeholder
3. Build Nomba payment webhook (curl-test it)
4. Demo: buyer texts → orders → you curl Nomba webhook → both phones notified
5. **Describe** onboarding in your pitch: "Sellers text 'I want to sell' and the bot guides them through setup"

**This is 100% acceptable for a hackathon.** Judges care more about a working buyer loop than a working onboarding flow.

---

## 12. Demo Day Script

### If You Have Onboarding Built:

1. **Text bot number:** "I want to sell" → complete onboarding → virtual account created
2. **Text seller number as buyer:** "Hi" → receive catalog
3. **Reply "1"** → product detail → "1" (Buy) → type quantity → cart summary
4. **Reply CONFIRM** → type address → order summary with real Nomba bank details
5. **Run curl** in terminal → Nomba webhook fires
6. **Both phones receive notification**

### If You Only Have Buyer Loop (Pre-seeded Seller):

1. **Explain:** "I have pre-seeded a seller called Amina Fabrics. In production, sellers onboard via WhatsApp."
2. **Text seller number as buyer:** "Hi" → receive catalog
3. **Reply "1"** → product detail → "1" (Buy) → type quantity → cart summary
4. **Reply CONFIRM** → type address → order summary with Nomba bank details
5. **Run curl** in terminal → payment webhook
6. **Both phones notified**
7. **Explain:** "Seller onboarding is the next feature — sellers text the bot, answer 4 questions, and their shop is live with a virtual account."

---

> **Meta API. Upstash. Vercel. Ship it.**
