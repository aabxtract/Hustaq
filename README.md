# HUSTAQ — Hackathon Edition

WhatsApp-native commerce platform for Nigerian informal sellers.

**Tech Stack:** Python 3.12 · FastAPI · Vercel · MongoDB Atlas · Upstash Redis · Meta WhatsApp Cloud API · Nomba Payments · httpx · Pydantic v2

---

## Table of Contents

1. [Product Overview & Core Demo Loop](#1-product-overview--core-demo-loop)
2. [Full Tech Stack](#2-full-tech-stack)
3. [Architecture Overview](#3-architecture-overview)
4. [GitHub Repository Structure](#4-github-repository-structure)
5. [Phase 1 Build — Core App Without Nomba](#5-phase-1-build--core-app-without-nomba)
6. [Phase 2 — Nomba Integration](#6-phase-2--nomba-integration)
7. [3-Day Build Flow](#7-3-day-build-flow)
8. [Environment Variables Reference](#8-environment-variables-reference)
9. [Full Build Checklist](#9-full-build-checklist)
10. [Demo Day Checklist](#10-demo-day-checklist)

---

## 1. Product Overview & Core Demo Loop

Hustaq is a WhatsApp-native commerce platform for Nigerian informal sellers. Sellers manage their entire shop by texting a WhatsApp bot number. Buyers message the seller's WhatsApp number; Hustaq intercepts those messages via Meta WhatsApp Cloud API, runs them through a Python state machine, and replies with product catalogs, order confirmations, and payment instructions. Payments flow through Nomba virtual accounts. When a buyer pays, Nomba fires a webhook, Hustaq confirms the order automatically, and both buyer and seller receive WhatsApp notifications — all without a website or app.

### Core Demo Loop

| Step | Flow |
|------|------|
| 1 | Seller texts Hustaq bot → onboarding completes → Nomba virtual account issued |
| 2 | Buyer messages seller WhatsApp → Meta webhook fires → FastAPI replies with catalog |
| 3 | Buyer selects product → confirms quantity → receives order summary with bank details |
| 4 | Buyer pays to Nomba virtual account via bank transfer |
| 5 | Nomba fires payment.success webhook → FastAPI confirms in under 2 seconds |
| 6 | Buyer gets receipt. Seller gets new order alert. Both via WhatsApp. |

### Build Strategy

Phase 1 first: build everything except Nomba. Get Meta WhatsApp receiving messages, the FastAPI state machine routing correctly, the full buyer conversation working end-to-end with a static bank placeholder, and seller commands functional. Only after the full conversation loop works cleanly do you add Phase 2 — Nomba virtual accounts and the payment webhook. This means you always have a working demo, even if Nomba integration hits a snag.

---

## 2. Full Tech Stack

| Category | Technology / Tool | Purpose |
|----------|------------------|---------|
| Language | Python 3.12 | Primary backend language. Type hints throughout. |
| Web Framework | FastAPI | HTTP routing, request parsing, dependency injection. Async-native. |
| Deployment | Vercel | Serverless hosting for FastAPI via API routes. |
| WhatsApp Layer | Meta WhatsApp Cloud API | Approved sender. Inbound webhooks + outbound message sends via Graph API. |
| Meta Graph API | httpx (async) | Send messages, media, templates via Meta's API. |
| HTTP Client | httpx | Async HTTP client for Nomba API calls. |
| Database | MongoDB Atlas | Primary storage. Collections: sellers, products, orders, conversations, payments. |
| DB Driver | Motor (async MongoDB) | Async MongoDB driver for Python. |
| Cache | Upstash Redis | Conversation state, onboarding state, Nomba token cache, idempotency keys. |
| Redis Client | redis-py | Python Redis client. `redis.from_url()` connection. |
| Data Validation | Pydantic v2 | Request/response models, env var parsing via BaseSettings. |
| Payments | Nomba API (sandbox) | Virtual account creation, payment.success webhooks. |
| Version Control | GitHub | Source control with tagged checkpoints per phase. |

### Full requirements.txt

```
fastapi==0.111.0
uvicorn==0.30.0
httpx==0.27.0
motor==3.4.0
pymongo==4.7.0
redis==5.0.4
pydantic==2.7.0
pydantic-settings==2.3.0
python-multipart==0.0.9
```

---

## 3. Architecture Overview

```
Meta WhatsApp Cloud API
    |
    | POST (webhook)
    v
Vercel Serverless Function (/api/webhooks/twilio)
    |
    v
FastAPI Router (src/handlers/twilio.py)
    |
    +--------> Motor ---------> MongoDB Atlas
    |
    +--------> redis-py ------> Upstash Redis
    |
    +--------> httpx ---------> Nomba API
    |
    +--------> Meta Graph API --> WhatsApp
```

### What You Need (Hackathon MVP)

- **Vercel account** (free tier works)
- **MongoDB Atlas** (free M0 cluster)
- **Upstash Redis** (free tier, serverless)
- **Meta WhatsApp Cloud API** (sandbox or approved sender)
- **Nomba** (sandbox credentials)

---

## 4. GitHub Repository Structure

```
hustaq/
├── api/
│   └── index.py              # Vercel entry point — mounts FastAPI app
│
├── src/
│   ├── handlers/
│   │   ├── twilio.py          # FastAPI router — Meta webhook receiver
│   │   └── nomba.py           # FastAPI router — Nomba payment webhook
│   │
│   ├── services/
│   │   ├── twilio.py          # send_message() via Meta Graph API
│   │   ├── nomba.py           # get_token(), create_virtual_account()
│   │   ├── state.py           # process_message() — full state machine
│   │   └── seller_commands.py # Seller onboarding + commands
│   │
│   ├── bot/
│   │   ├── scripts.py         # SCRIPTS dict — every buyer + seller message
│   │   └── intent.py          # classify_intent(message, state) -> Intent
│   │
│   ├── db/
│   │   ├── client.py          # Motor async client singleton
│   │   └── queries.py         # All DB read/write functions
│   │
│   └── lib/
│       ├── config.py          # Pydantic Settings — all env vars
│       └── redis_client.py    # Upstash Redis connection singleton
│
├── docs/
│   └── DEMO_SCRIPT.md         # Exact messages to type on demo day
│
├── api/
│   └── index.py               # Vercel serverless function entry point
├── seed.py                    # MongoDB seed script
├── vercel.json                # Vercel config
├── requirements.txt
└── README.md
```

### Solo Git Workflow

- Commit after every working unit, not at end of day. `feat: meta webhook receives and logs messages` is a good commit.
- Never commit broken code. If something is mid-way: `git stash`
- Tag clean states before risky changes: `git tag v0.1-webhook-working`
- Before adding Nomba: `git tag v0.2-pre-nomba` — clean rollback point if Nomba breaks anything

---

## 5. Phase 1 Build — Core App Without Nomba

Phase 1 exit condition: a buyer texts your Meta WhatsApp number, sees the catalog, selects a product, confirms quantity, gives their address, and receives an order summary with a static bank placeholder. The order document exists in MongoDB with status `pending`. Everything below must work before you touch Nomba.

### 5.1 Vercel Setup

| Task | Notes |
|------|-------|
| Create Vercel account | Free tier is fine |
| Connect GitHub repo | Import project in Vercel dashboard |
| Set all env vars in Vercel | See Section 8 |
| Configure build settings | Framework: Other, Build Command: empty, Output Directory: `.` |
| Deploy | `vercel --prod` or push to main branch |

### 5.2 MongoDB Atlas Setup

| Task | Notes |
|------|-------|
| Create MongoDB Atlas account | cloud.mongodb.com |
| Create M0 free cluster | Choose any region (AWS/GCP) |
| Create database user | Note username and password |
| Whitelist IP addresses | Allow access from anywhere (0.0.0.0/0) for hackathon |
| Get connection string | `mongodb+srv://<user>:<pass>@cluster.mongodb.net/hustaq` |

### 5.3 Database Collections & Seed Data

No schema migration needed. MongoDB is schemaless. Collections are created automatically when you insert documents.

**sellers collection:**
```json
{
  "_id": ObjectId,
  "phone_number": "+2348012345678",
  "shop_name": "Amina Fabrics",
  "shop_slug": "amina-fabrics",
  "category": "fashion",
  "location": "Yaba Lagos",
  "twilio_number": "whatsapp:+234YOURBOTNUMBER",
  "bot_paused": false,
  "balance_kobo": 0,
  "pending_balance_kobo": 0,
  "nomba_virtual_account": null,
  "nomba_bank_name": null,
  "nomba_bank_code": null,
  "created_at": ISODate
}
```

**products collection:**
```json
{
  "_id": ObjectId,
  "seller_id": ObjectId,
  "name": "Hollandaise Ankara",
  "price_kobo": 850000,
  "stock_count": 20,
  "photo_url": "https://placehold.co/400",
  "visible": true,
  "created_at": ISODate
}
```

**orders collection:**
```json
{
  "_id": ObjectId,
  "order_number": "ORD-001",
  "seller_id": ObjectId,
  "buyer_phone": "+2348051234567",
  "items": [
    {"product_id": ObjectId, "name": "Hollandaise Ankara", "qty": 3, "price_kobo": 850000}
  ],
  "subtotal_kobo": 2550000,
  "total_kobo": 2550000,
  "status": "pending",
  "payment_status": "unpaid",
  "nomba_reference": null,
  "delivery_address": "",
  "created_at": ISODate
}
```

**conversations collection:**
```json
{
  "_id": ObjectId,
  "seller_id": ObjectId,
  "seller_whatsapp_number": "whatsapp:+2348001234567",
  "buyer_phone": "+2348051234567",
  "state": "idle",
  "cart": {},
  "selected_product": null,
  "pending_order_id": null,
  "handoff_active": false,
  "last_message_at": ISODate
}
```

**payments collection:**
```json
{
  "_id": ObjectId,
  "order_id": ObjectId,
  "seller_id": ObjectId,
  "buyer_phone": "+2348051234567",
  "amount_kobo": 2550000,
  "status": "pending",
  "nomba_reference": "NOM-TEST-001",
  "created_at": ISODate
}
```

**Seed data** — run this Python script once after deploying:
```python
# seed.py
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from datetime import datetime, timezone

async def seed():
    client = AsyncIOMotorClient(os.environ["MONGODB_URI"])
    db = client.hustaq

    # Seed seller
    await db.sellers.update_one(
        {"phone_number": "+2348012345678"},
        {"$setOnInsert": {
            "phone_number": "+2348012345678",
            "shop_name": "Amina Fabrics",
            "shop_slug": "amina-fabrics",
            "category": "fashion",
            "location": "Yaba Lagos",
            "twilio_number": os.environ["META_BOT_NUMBER"],
            "bot_paused": False,
            "balance_kobo": 0,
            "pending_balance_kobo": 0,
            "nomba_virtual_account": None,
            "nomba_bank_name": None,
            "nomba_bank_code": None,
            "created_at": datetime.now(timezone.utc),
        }},
        upsert=True,
    )

    seller = await db.sellers.find_one({"shop_slug": "amina-fabrics"})

    # Seed product
    await db.products.update_one(
        {"seller_id": seller["_id"], "name": "Hollandaise Ankara"},
        {"$setOnInsert": {
            "seller_id": seller["_id"],
            "name": "Hollandaise Ankara",
            "price_kobo": 850000,
            "stock_count": 20,
            "photo_url": "https://placehold.co/400",
            "visible": True,
            "created_at": datetime.now(timezone.utc),
        }},
        upsert=True,
    )

    print("Seed complete!")
    client.close()

asyncio.run(seed())
```

### 5.4 Project Scaffold & Dependencies

```bash
# Create project and virtual environment
mkdir hustaq && cd hustaq
python3.12 -m venv .venv
source .venv/bin/activate

# Install all dependencies
pip install fastapi uvicorn httpx motor pymongo \
    pydantic pydantic-settings python-multipart redis
pip freeze > requirements.txt
```

```python
# main.py — FastAPI app entry point
from fastapi import FastAPI
from src.handlers.twilio import router as whatsapp_router
from src.handlers.nomba import router as nomba_router

app = FastAPI(title="Hustaq")
app.include_router(whatsapp_router, prefix="/api/webhooks")
app.include_router(nomba_router, prefix="/api/webhooks")

# Also mount at /webhooks for backward compatibility
app.include_router(whatsapp_router, prefix="/webhooks")
app.include_router(nomba_router, prefix="/webhooks")

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/api/health")
async def api_health():
    return {"status": "ok"}
```

### 5.5 Vercel Configuration

```json
// vercel.json
{
  "builds": [
    {
      "src": "api/index.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/api/(.*)",
      "dest": "api/index.py"
    }
  ]
}
```

```python
# api/index.py — Vercel entry point
from main import app

# Vercel expects a handler named "app"
```

### 5.6 Lib Layer — Config, DB Client, Redis Client

```python
# src/lib/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    MONGODB_URI: str = "mongodb://localhost:27017/hustaq"
    UPSTASH_REDIS_URL: str = "redis://localhost:6379"
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_WHATSAPP_NUMBER: str = "whatsapp:+14155238886"
    NOMBA_CLIENT_ID: str = ""
    NOMBA_CLIENT_SECRET: str = ""
    NOMBA_ENV: str = "sandbox"
    VERCEL_URL: str = ""

    class Config:
        env_file = ".env"

_settings = None

def get_settings():
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
```

```python
# src/lib/redis_client.py
import redis
from src.lib.config import get_settings

_client = None

def get_redis():
    global _client
    if _client is None:
        settings = get_settings()
        _client = redis.from_url(settings.UPSTASH_REDIS_URL, decode_responses=True)
    return _client
```

```python
# src/db/client.py
import motor.motor_asyncio
from src.lib.config import settings

_client: motor.motor_asyncio.AsyncIOMotorClient | None = None
_db = None

def get_db():
    global _client, _db
    if _client is None:
        _client = motor.motor_asyncio.AsyncIOMotorClient(settings.MONGODB_URI)
        _db = _client.hustaq
    return _db
```

```python
# src/db/queries.py
from src.db.client import get_db
from datetime import datetime, timezone

# --- Sellers ---
async def get_seller_by_phone(phone_number: str) -> dict | None:
    return await get_db().sellers.find_one({"phone_number": phone_number})

async def get_seller_by_twilio_number(twilio_number: str) -> dict | None:
    return await get_db().sellers.find_one({"twilio_number": twilio_number})

async def create_seller(phone_number: str, shop_name: str, shop_slug: str) -> dict:
    doc = {
        "phone_number": phone_number,
        "shop_name": shop_name,
        "shop_slug": shop_slug,
        "category": "",
        "location": "",
        "twilio_number": "",
        "bot_paused": False,
        "balance_kobo": 0,
        "pending_balance_kobo": 0,
        "nomba_virtual_account": None,
        "nomba_bank_name": None,
        "nomba_bank_code": None,
        "created_at": datetime.now(timezone.utc),
    }
    result = await get_db().sellers.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc

async def update_seller(seller_id, updates: dict):
    await get_db().sellers.update_one({"_id": seller_id}, {"$set": updates})

# --- Products ---
async def get_products_by_seller(seller_id) -> list[dict]:
    cursor = get_db().products.find({"seller_id": seller_id, "visible": True}).sort("created_at", 1)
    return await cursor.to_list(length=100)

async def create_product(seller_id, name: str, price_kobo: int, stock_count: int, photo_url: str) -> dict:
    doc = {
        "seller_id": seller_id,
        "name": name,
        "price_kobo": price_kobo,
        "stock_count": stock_count,
        "photo_url": photo_url,
        "visible": True,
        "created_at": datetime.now(timezone.utc),
    }
    result = await get_db().products.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc

async def get_product_by_id(product_id) -> dict | None:
    return await get_db().products.find_one({"_id": product_id})

# --- Conversations ---
async def get_conversation(seller_id, buyer_phone: str) -> dict | None:
    return await get_db().conversations.find_one({
        "seller_id": seller_id,
        "buyer_phone": buyer_phone,
    })

async def create_conversation(seller_id, seller_wa: str, buyer_phone: str) -> dict:
    doc = {
        "seller_id": seller_id,
        "seller_whatsapp_number": seller_wa,
        "buyer_phone": buyer_phone,
        "state": "idle",
        "cart": {},
        "selected_product": None,
        "pending_order_id": None,
        "handoff_active": False,
        "last_message_at": datetime.now(timezone.utc),
    }
    result = await get_db().conversations.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc

async def update_conversation(conv_id, updates: dict):
    updates["last_message_at"] = datetime.now(timezone.utc)
    await get_db().conversations.update_one({"_id": conv_id}, {"$set": updates})

# --- Orders ---
async def create_order(seller_id, buyer_phone: str, items: list, subtotal_kobo: int,
                       total_kobo: int, delivery_address: str) -> dict:
    order_count = await get_db().orders.count_documents({"seller_id": seller_id})
    doc = {
        "order_number": f"ORD-{order_count + 1:03d}",
        "seller_id": seller_id,
        "buyer_phone": buyer_phone,
        "items": items,
        "subtotal_kobo": subtotal_kobo,
        "total_kobo": total_kobo,
        "status": "pending",
        "payment_status": "unpaid",
        "nomba_reference": None,
        "delivery_address": delivery_address,
        "created_at": datetime.now(timezone.utc),
    }
    result = await get_db().orders.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc

async def get_order_by_id(order_id) -> dict | None:
    return await get_db().orders.find_one({"_id": order_id})

async def get_orders_by_seller(seller_id, limit: int = 5) -> list[dict]:
    cursor = get_db().orders.find({"seller_id": seller_id}).sort("created_at", -1).limit(limit)
    return await cursor.to_list(length=limit)

async def update_order(order_id, updates: dict):
    await get_db().orders.update_one({"_id": order_id}, {"$set": updates})

# --- Payments ---
async def create_payment(order_id, seller_id, buyer_phone: str, amount_kobo: int, nomba_reference: str) -> dict:
    doc = {
        "order_id": order_id,
        "seller_id": seller_id,
        "buyer_phone": buyer_phone,
        "amount_kobo": amount_kobo,
        "status": "pending",
        "nomba_reference": nomba_reference,
        "created_at": datetime.now(timezone.utc),
    }
    result = await get_db().payments.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc

async def get_payment_by_reference(nomba_reference: str) -> dict | None:
    return await get_db().payments.find_one({"nomba_reference": nomba_reference})

async def update_payment(payment_id, updates: dict):
    await get_db().payments.update_one({"_id": payment_id}, {"$set": updates})
```

### 5.7 Twilio Webhook Handler

```python
# src/handlers/twilio.py
from fastapi import APIRouter, Request, Response
from src.lib.config import settings
from src.db.queries import get_seller_by_twilio_number
from src.services.state import process_message
from src.services.twilio import send_message, verify_twilio_signature
from src.bot.scripts import SCRIPTS

router = APIRouter()

@router.post("/twilio")
async def twilio_webhook(request: Request):
    # 1. Parse form-encoded body (Twilio sends application/x-www-form-urlencoded)
    form = await request.form()
    params = dict(form)

    # 2. Verify Twilio signature
    signature = request.headers.get("X-Twilio-Signature", "")
    url = str(request.url)
    if not verify_twilio_signature(settings.TWILIO_AUTH_TOKEN, signature, url, params):
        return Response(status_code=403)

    # 3. Extract fields
    from_phone = params["From"].replace("whatsapp:", "")
    to_phone = params["To"].replace("whatsapp:", "")
    text = params.get("Body", "")
    media_url = params.get("MediaUrl0")

    # 4. Echo detection — seller chatting manually from their own phone
    seller = await get_seller_by_twilio_number(f"whatsapp:{to_phone}")
    if seller and from_phone == seller["phone_number"]:
        from src.handlers.twilio import handle_echo
        await handle_echo(seller, from_phone)
        return Response(content="", status_code=200)

    # 5. Route seller bot commands (message TO Hustaq central number)
    hustaq_number = settings.TWILIO_WHATSAPP_NUMBER.replace("whatsapp:", "")
    if to_phone == hustaq_number:
        from src.services.seller_commands import handle_seller_command
        await handle_seller_command(from_phone, text, media_url)
        return Response(content="", status_code=200)

    # 6. Normal buyer message — run through state machine
    await process_message(from_phone, to_phone, text, media_url)
    return Response(content="", status_code=200)


async def handle_echo(seller: dict, seller_phone: str):
    from src.db.queries import update_conversation, get_conversation
    conv = await get_conversation(seller["_id"], seller_phone)
    if conv:
        await update_conversation(conv["_id"], {"handoff_active": True})
    await send_message(seller_phone, SCRIPTS["seller"]["echo_pause"]("your buyer"))
```

### 5.8 Twilio Send Service

```python
# src/services/twilio.py
from twilio.rest import Client
from twilio.request_validator import RequestValidator
from src.lib.config import settings

_client: Client | None = None

def get_client() -> Client:
    global _client
    if _client is None:
        _client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    return _client

async def send_message(to: str, body: str) -> None:
    client = get_client()
    from_number = settings.TWILIO_WHATSAPP_NUMBER
    to_formatted = to if to.startswith("whatsapp:") else f"whatsapp:{to}"
    client.messages.create(from_=from_number, to=to_formatted, body=body)

def verify_twilio_signature(
    auth_token: str, signature: str, url: str, params: dict
) -> bool:
    validator = RequestValidator(auth_token)
    return validator.validate(url, params, signature)
```

### 5.9 Bot Scripts Map

```python
# src/bot/scripts.py
# Every message Hustaq sends lives here. Plain text only — no markdown.

SCRIPTS = {
    "buyer": {
        "IDLE_greeting": lambda shop_name, catalog: (
            f"Hi! Welcome to {shop_name}. Here is what we have:\n\n{catalog}\n\n"
            "Reply a number to order!"
        ),
        "BROWSE_catalog": lambda items: "\n".join(
            f"{i+1}. {p['name']} - N{p['price_kobo']//100:,}"
            for i, p in enumerate(items)
        ),
        "SELECT_product": lambda name, price, stock: (
            f"{name} - N{price:,}\n{stock} in stock.\n\n"
            "1. Buy now\n2. Ask a question\n3. Back to catalog"
        ),
        "CART_quantity": lambda max_stock: f"How many? (Max {max_stock})",
        "CART_summary": lambda qty, price, subtotal: (
            f"{qty} x N{price:,} = N{subtotal:,}\nReply CONFIRM to proceed."
        ),
        "CHECKOUT_address": lambda: (
            "Delivery to?\n1. Type your address\n2. Send your location"
        ),
        "CONFIRM_payment": lambda shop_name, bank, acct, total: (
            f"Order Summary\nTotal: N{total:,}\n\nPay to:\n{shop_name}\n"
            f"{bank} - {acct}\n\nReply PAID when you have transferred."
        ),
        "CONFIRM_received": lambda order_num: (
            f"Payment received! Order #{order_num} confirmed.\n"
            "We will notify you when it ships."
        ),
        "CONFIRM_checking": lambda: "Checking your payment... one moment.",
        "CANCEL_order": lambda: "Order cancelled. Reply MENU to start again.",
        "INVALID_input": lambda: "Sorry, I did not get that. Reply MENU to start over.",
        "HANDOFF_notify": lambda name: f"Connecting you to {name} now.",
        "OUT_OF_STOCK": lambda left: f"Only {left} left. How many would you like?",
    },
    "seller": {
        "menu": lambda shop_name: (
            f"{shop_name} - Hustaq\n\n"
            "1. Add Product\n2. View Orders\n3. Check Balance\n4. Settings\n\n"
            "Reply a number."
        ),
        "new_order": lambda num, total, phone, addr: (
            f"New order #{num} - N{total:,} - PAID\nBuyer: {phone}\nAddress: {addr}"
        ),
        "balance": lambda avail, pending: (
            f"Available: N{avail:,}\nPending: N{pending:,} (settles in 24h)\n\n"
            "Reply WITHDRAW to transfer."
        ),
        "order_list": lambda orders: (
            "No orders yet!" if not orders else
            "\n".join(f'{i+1}. #{o["order_number"]} N{o["total_kobo"]//100:,} {o["status"].upper()}'
                      for i, o in enumerate(orders))
        ),
        "pause_confirmed": lambda: "Bot paused. Reply RESUME when done.",
        "resume_confirmed": lambda: "Bot is back on. I will handle buyers for you.",
        "echo_pause": lambda buyer: (
            f"You are chatting with {buyer}. Bot paused. Reply RESUME when done."
        ),
        "onboarding_welcome": lambda: (
            "Welcome to Hustaq! I will answer buyers, take orders, and confirm payments.\n"
            "Ready? Reply YES."
        ),
        "onboarding_shopname": lambda: "What is your shop name?",
        "onboarding_category": lambda: (
            "What do you sell?\n1. Fashion\n2. Food and Drinks\n"
            "3. Beauty\n4. Gadgets\n5. Other"
        ),
        "onboarding_location": lambda: "Where are you based? (e.g. Yaba Lagos)",
        "onboarding_done": lambda shop: (
            f"{shop} is live! Send a photo to add your first product."
        ),
        "payment_ready": lambda shop, bank, acct: (
            f"Your payment account is ready.\nBuyers pay to: {shop} - {bank} - {acct}"
        ),
    }
}
```

### 5.10 Intent Classifier

```python
# src/bot/intent.py
from typing import Literal

Intent = Literal[
    "BROWSE", "SELECT", "QUANTITY", "CHECKOUT", "CONFIRM",
    "CANCEL", "GREETING", "HANDOFF", "TRACK", "PAID", "UNKNOWN"
]

PATTERNS: dict[str, list[str]] = {
    "GREETING": ["hi", "hello", "hey", "good morning", "good afternoon", "good evening", "oya", "sup"],
    "BROWSE": ["what", "have", "products", "catalog", "show", "list", "menu", "options", "items", "see"],
    "SELECT": ["1", "2", "3", "4", "5", "first", "second", "third", "that one", "this one"],
    "QUANTITY": ["how many", "give me", "i want", "send me", "order", "yards", "pieces", "units", "bags"],
    "CHECKOUT": ["buy", "checkout", "proceed", "done", "go ahead"],
    "CONFIRM": ["confirm"],
    "PAID": ["paid", "i paid", "i have paid", "transferred", "sent", "done"],
    "CANCEL": ["cancel", "stop", "no", "never mind", "change mind", "nope"],
    "TRACK": ["where", "track", "status", "delivery", "shipped", "when", "update"],
    "HANDOFF": ["speak to", "talk to", "call", "human", "agent", "real person", "manager", "owner"],
}

def classify_intent(message: str, current_state: str) -> Intent:
    m = message.strip().lower()
    if current_state == "browse" and m.isdigit():
        return "SELECT"
    if current_state == "select" and m == "1":
        return "CHECKOUT"
    if current_state == "cart" and m.isdigit():
        return "QUANTITY"
    if current_state == "confirm" and any(p in m for p in PATTERNS["PAID"]):
        return "PAID"
    for intent, patterns in PATTERNS.items():
        if any(p in m for p in patterns):
            return intent  # type: ignore
    return "UNKNOWN"
```

### 5.11 State Machine

```python
# src/services/state.py
from src.bot.intent import classify_intent
from src.bot.scripts import SCRIPTS
from src.services.twilio import send_message
from src.db.queries import (
    get_seller_by_twilio_number, get_conversation, create_conversation,
    update_conversation, get_products_by_seller, get_product_by_id,
    create_order, update_order,
)

async def process_message(
    from_phone: str, to_phone: str,
    text: str, media_url: str | None
):
    seller = await get_seller_by_twilio_number(f"whatsapp:{to_phone}")
    if not seller:
        return
    if seller["bot_paused"]:
        return

    conv = await get_or_create_conv(seller["_id"], f"whatsapp:{to_phone}", from_phone)
    if conv["handoff_active"]:
        return

    intent = classify_intent(text, conv["state"])
    state = conv["state"]

    if state == "idle":
        await handle_idle(seller, conv, intent, from_phone)
    elif state == "browse":
        await handle_browse(seller, conv, intent, text, from_phone)
    elif state == "select":
        await handle_select(seller, conv, intent, text, from_phone)
    elif state == "cart":
        await handle_cart(seller, conv, intent, text, from_phone)
    elif state == "checkout":
        await handle_checkout(seller, conv, intent, from_phone)
    elif state == "delivery":
        await handle_delivery(seller, conv, text, from_phone)
    elif state == "confirm":
        await handle_confirm(seller, conv, intent, from_phone)


async def get_or_create_conv(seller_id, seller_wa: str, buyer_phone: str) -> dict:
    conv = await get_conversation(seller_id, buyer_phone)
    if conv:
        return conv
    return await create_conversation(seller_id, seller_wa, buyer_phone)


async def handle_idle(seller, conv, intent, buyer):
    products = await get_products_by_seller(seller["_id"])
    catalog = SCRIPTS["buyer"]["BROWSE_catalog"](products)
    await update_conversation(conv["_id"], {"state": "browse"})
    await send_message(buyer, SCRIPTS["buyer"]["IDLE_greeting"](seller["shop_name"], catalog))


async def handle_browse(seller, conv, intent, text, buyer):
    if intent != "SELECT":
        return await send_message(buyer, SCRIPTS["buyer"]["INVALID_input"]())
    idx = int(text.strip()) - 1
    products = await get_products_by_seller(seller["_id"])
    if idx < 0 or idx >= len(products):
        return await send_message(buyer, SCRIPTS["buyer"]["INVALID_input"]())
    product = products[idx]
    await update_conversation(conv["_id"], {
        "state": "select",
        "selected_product": {
            "product_id": str(product["_id"]),
            "name": product["name"],
            "price_kobo": product["price_kobo"],
            "stock": product["stock_count"],
        },
    })
    await send_message(buyer, SCRIPTS["buyer"]["SELECT_product"](
        product["name"], product["price_kobo"] // 100, product["stock_count"]))


async def handle_select(seller, conv, intent, text, buyer):
    if intent == "CHECKOUT":
        await update_conversation(conv["_id"], {"state": "cart"})
        selected = conv.get("selected_product") or {}
        max_stock = selected.get("stock", 0)
        await send_message(buyer, SCRIPTS["buyer"]["CART_quantity"](max_stock))
    elif intent == "BROWSE":
        products = await get_products_by_seller(seller["_id"])
        catalog = SCRIPTS["buyer"]["BROWSE_catalog"](products)
        await update_conversation(conv["_id"], {"state": "browse"})
        await send_message(buyer, SCRIPTS["buyer"]["IDLE_greeting"](seller["shop_name"], catalog))
    else:
        await send_message(buyer, SCRIPTS["buyer"]["INVALID_input"]())


async def handle_cart(seller, conv, intent, text, buyer):
    selected = conv.get("selected_product") or {}
    qty = int(text.strip())
    max_stock = selected.get("stock", 0)
    if qty < 1 or qty > max_stock:
        return await send_message(buyer, SCRIPTS["buyer"]["OUT_OF_STOCK"](max_stock))
    price = selected.get("price_kobo", 0) // 100
    subtotal = qty * price
    await update_conversation(conv["_id"], {
        "state": "checkout",
        "cart": {"qty": qty, "price_kobo": selected.get("price_kobo", 0), "subtotal": subtotal},
    })
    await send_message(buyer, SCRIPTS["buyer"]["CART_summary"](qty, price, subtotal))


async def handle_checkout(seller, conv, intent, buyer):
    if intent == "CONFIRM":
        await update_conversation(conv["_id"], {"state": "delivery"})
        await send_message(buyer, SCRIPTS["buyer"]["CHECKOUT_address"]())
    elif intent == "CANCEL":
        await update_conversation(conv["_id"], {"state": "idle", "cart": {}, "selected_product": None})
        await send_message(buyer, SCRIPTS["buyer"]["CANCEL_order"]())
    else:
        await send_message(buyer, SCRIPTS["buyer"]["INVALID_input"]())


async def handle_delivery(seller, conv, text, buyer):
    cart = conv.get("cart", {})
    selected = conv.get("selected_product", {})

    items = [{
        "product_id": selected.get("product_id"),
        "name": selected.get("name"),
        "qty": cart.get("qty", 0),
        "price_kobo": cart.get("price_kobo", 0),
    }]
    total_kobo = cart.get("qty", 0) * cart.get("price_kobo", 0)

    order = await create_order(
        seller["_id"], buyer, items, total_kobo, total_kobo, text
    )

    bank = seller.get("nomba_bank_name") or "Bank TBA"
    acct = seller.get("nomba_virtual_account") or "Account TBA"

    await update_conversation(conv["_id"], {
        "state": "confirm",
        "pending_order_id": str(order["_id"]),
    })
    await send_message(buyer, SCRIPTS["buyer"]["CONFIRM_payment"](
        seller["shop_name"], bank, acct, total_kobo // 100))


async def handle_confirm(seller, conv, intent, buyer):
    if intent == "PAID":
        pending_id = conv.get("pending_order_id")
        if pending_id:
            from bson import ObjectId
            await update_order(ObjectId(pending_id), {"payment_status": "checking"})
        await send_message(buyer, SCRIPTS["buyer"]["CONFIRM_checking"]())
    elif intent == "CANCEL":
        pending_id = conv.get("pending_order_id")
        if pending_id:
            from bson import ObjectId
            await update_order(ObjectId(pending_id), {"status": "cancelled"})
        await update_conversation(conv["_id"], {"state": "idle", "cart": {}, "selected_product": None})
        await send_message(buyer, SCRIPTS["buyer"]["CANCEL_order"]())
    else:
        await send_message(buyer, SCRIPTS["buyer"]["INVALID_input"]())
```

### 5.12 Seller Commands & Onboarding

```python
# src/services/seller_commands.py
from src.db.queries import (
    get_seller_by_phone, create_seller, update_seller,
    get_orders_by_seller, get_products_by_seller, create_product,
)
from src.bot.scripts import SCRIPTS
from src.services.twilio import send_message
from src.lib.config import settings

# In-memory onboarding state (for hackathon simplicity — no Redis needed)
# Maps phone_number -> onboarding step
_onboarding_state: dict[str, dict] = {}


async def handle_seller_command(seller_phone: str, text: str, media_url: str | None):
    seller = await get_seller_by_phone(seller_phone)

    if not seller:
        return await start_onboarding(seller_phone)

    # Check if seller is in onboarding flow
    if seller_phone in _onboarding_state:
        return await continue_onboarding(seller, seller_phone, text)

    cmd = text.strip().lower()

    if cmd in ("menu", "0"):
        await send_message(seller_phone, SCRIPTS["seller"]["menu"](seller["shop_name"]))
    elif cmd in ("2", "view orders"):
        orders = await get_orders_by_seller(seller["_id"])
        await send_message(seller_phone, SCRIPTS["seller"]["order_list"](orders))
    elif cmd in ("3", "check balance"):
        await send_message(seller_phone, SCRIPTS["seller"]["balance"](
            seller["balance_kobo"] // 100, seller["pending_balance_kobo"] // 100))
    elif cmd == "pause":
        await update_seller(seller["_id"], {"bot_paused": True})
        await send_message(seller_phone, SCRIPTS["seller"]["pause_confirmed"]())
    elif cmd == "resume":
        await update_seller(seller["_id"], {"bot_paused": False})
        await send_message(seller_phone, SCRIPTS["seller"]["resume_confirmed"]())
    elif media_url:
        await handle_product_photo(seller, seller_phone, media_url)
    else:
        await send_message(seller_phone, SCRIPTS["seller"]["menu"](seller["shop_name"]))


async def start_onboarding(seller_phone: str):
    seller = await create_seller(seller_phone, "New Shop", f"shop-{seller_phone[-4:]}")
    _onboarding_state[seller_phone] = {"step": "WELCOME", "seller_id": str(seller["_id"])}
    await send_message(seller_phone, SCRIPTS["seller"]["onboarding_welcome"]())


async def continue_onboarding(seller, seller_phone: str, text: str):
    state = _onboarding_state[seller_phone]
    step = state["step"]

    if step == "WELCOME":
        if text.strip().lower() in ("yes", "y"):
            state["step"] = "SHOP_NAME"
            await send_message(seller_phone, SCRIPTS["seller"]["onboarding_shopname"]())
        else:
            await send_message(seller_phone, "Reply YES to get started!")
    elif step == "SHOP_NAME":
        state["shop_name"] = text.strip()
        state["step"] = "CATEGORY"
        await send_message(seller_phone, SCRIPTS["seller"]["onboarding_category"]())
    elif step == "CATEGORY":
        categories = {"1": "Fashion", "2": "Food and Drinks", "3": "Beauty", "4": "Gadgets", "5": "Other"}
        category = categories.get(text.strip(), "Other")
        await update_seller(seller["_id"], {
            "shop_name": state["shop_name"],
            "shop_slug": state["shop_name"].lower().replace(" ", "-"),
            "category": category,
        })
        state["step"] = "LOCATION"
        await send_message(seller_phone, SCRIPTS["seller"]["onboarding_location"]())
    elif step == "LOCATION":
        await update_seller(seller["_id"], {"location": text.strip()})
        del _onboarding_state[seller_phone]
        await send_message(seller_phone, SCRIPTS["seller"]["onboarding_done"](state["shop_name"]))


async def handle_product_photo(seller, seller_phone: str, media_url: str):
    # For hackathon MVP: store the Twilio media URL directly
    # No S3 needed — Twilio media URLs are accessible for a few days
    _onboarding_state[seller_phone] = {
        "step": "PRODUCT_NAME",
        "photo_url": media_url,
        "seller_id": str(seller["_id"]),
    }
    await send_message(seller_phone, "Got the photo! What is the product name?")


# Extend product photo flow inline
_original_continue = continue_onboarding

async def continue_onboarding(seller, seller_phone: str, text: str):
    state = _onboarding_state.get(seller_phone)
    if not state:
        return

    if state.get("step") == "PRODUCT_NAME":
        state["product_name"] = text.strip()
        state["step"] = "PRODUCT_PRICE"
        await send_message(seller_phone, "What is the price in Naira?")
        return

    if state.get("step") == "PRODUCT_PRICE":
        price_kobo = int(text.strip()) * 100
        await create_product(
            seller["_id"],
            state["product_name"],
            price_kobo,
            10,  # default stock
            state["photo_url"],
        )
        del _onboarding_state[seller_phone]
        await send_message(seller_phone, f'{state["product_name"]} added to your shop!')
        return

    # Fall through to original onboarding flow
    await _original_continue(seller, seller_phone, text)
```

---

## 6. Phase 2 — Nomba Integration

Start Phase 2 only after the Phase 1 exit condition passes cleanly. Add Nomba in this exact order — each step builds on the previous one.

### Step 1: Nomba token service

Create `src/services/nomba.py`. Write `get_nomba_token()` using httpx to POST `/auth/token/issue` with `grant_type=client_credentials`. Cache the token in Redis as `nomba:token` with 3500s TTL. Nomba credentials come from environment variables. Sandbox base URL: `https://api.sandbox.nomba.com/v1`

```python
# src/services/nomba.py
import httpx
from src.lib.config import get_settings
from src.lib.redis_client import get_redis

SANDBOX_URL = "https://api.sandbox.nomba.com/v1"
PROD_URL = "https://api.nomba.com/v1"

def _base_url():
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
    data = resp.json()["data"]
    r.setex("nomba:token", 3500, data["access_token"])
    return data["access_token"]
```

### Step 2: Virtual account creation

Write `create_virtual_account(seller_id, shop_name)`. POST `/accounts/virtual` with `accountName`, `currency='NGN'`, `accountRef=seller_id`, `callbackUrl`. On success update sellers document: `nomba_virtual_account`, `nomba_bank_name`, `nomba_bank_code`. Call this at the end of seller onboarding after location is saved.

```python
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
```

### Step 3: Real bank details in order summary

In `handle_delivery()` inside `state.py`, replace the static bank placeholder with the seller's real `nomba_virtual_account` and `nomba_bank_name` from the sellers document. The `SCRIPTS['buyer']['CONFIRM_payment']` already accepts these as arguments.

### Step 4: Nomba payment.success webhook handler

Create `src/handlers/nomba.py` with a FastAPI POST `/nomba` route. On `payment.success`: check Redis key `nomba:processed:{reference}` — skip if exists. Set key with 86400s TTL. Check MongoDB payments collection as fallback. Update orders.status=`paid`, payments.status=`success`. Add amount to sellers.balance_kobo. Call `send_message()` twice: buyer receipt + seller order alert. Return 200.

```python
# src/handlers/nomba.py
from fastapi import APIRouter, Request, Response
from src.db.queries import (
    get_payment_by_reference, create_payment,
    get_order_by_id, update_order,
    update_seller, get_seller_by_phone,
)
from src.services.twilio import send_message
from src.bot.scripts import SCRIPTS
from src.lib.redis_client import get_redis
from bson import ObjectId

router = APIRouter()

@router.post("/nomba")
async def nomba_webhook(request: Request):
    body = await request.json()
    event = body.get("event")

    if event != "payment.success":
        return Response(content="", status_code=200)

    data = body["data"]
    reference = data["reference"]

    # Idempotency — Redis fast check + MongoDB fallback
    r = get_redis()
    idem_key = f"nomba:processed:{reference}"
    if r.get(idem_key):
        return Response(content="", status_code=200)

    existing = await get_payment_by_reference(reference)
    if existing:
        r.setex(idem_key, 86400, "1")
        return Response(content="", status_code=200)

    r.setex(idem_key, 86400, "1")

    order_id = ObjectId(data["orderId"])
    amount_kobo = int(float(data["amount"]) * 100)
    customer = data.get("customer", {})

    order = await get_order_by_id(order_id)
    if not order:
        return Response(content="", status_code=404)

    await create_payment(
        order_id, order["seller_id"],
        customer.get("phone", ""), amount_kobo, reference
    )
    await update_order(order_id, {"status": "paid", "payment_status": "paid"})
    await update_seller(order["seller_id"], {"$inc": {"balance_kobo": amount_kobo}})

    effective_buyer = customer.get("phone", "") or order.get("buyer_phone", "")
    if effective_buyer:
        await send_message(effective_buyer, SCRIPTS["buyer"]["CONFIRM_received"](order["order_number"]))

    seller = await get_seller_by_phone(order["seller_id"])
    if seller:
        await send_message(seller["phone_number"], SCRIPTS["seller"]["new_order"](
            order["order_number"], amount_kobo // 100,
            effective_buyer, order.get("delivery_address", ""),
        ))

    return Response(content="", status_code=200)
```

### Step 5: Git tag + full loop test

```bash
git tag v1.0-nomba-integrated
```

Run complete demo: seller onboards → virtual account created → buyer orders → curl the Nomba webhook → both phones receive notification.

### Nomba Webhook Test Command

```bash
# Simulate Nomba payment.success to test your handler
# Replace ORDER_ID with a real order ID from your DB
curl -X POST https://your-project.vercel.app/api/webhooks/nomba \
  -H 'Content-Type: application/json' \
  -d '{
    "event": "payment.success",
    "data": {
      "reference": "NOM-TEST-001",
      "orderId": "ORDER_ID_HERE",
      "amount": "25500",
      "status": "success",
      "customer": { "name": "Chijioke", "phone": "+2348051234567" }
    }
  }'
```

---

## 7. 3-Day Build Flow

Every day has a clear exit condition. Do not move to the next day until the exit condition passes. Commit after every working unit. Tag the repo at each exit condition.

### 7.1 Day 1 — Infrastructure + Entry Points

**Goal:** A WhatsApp message fires your webhook, Vercel receives it, logs it, and replies.

| Build | Test |
|-------|------|
| Create MongoDB Atlas M0 cluster | Send WhatsApp to Twilio number — confirm webhook fires |
| Create Upstash Redis instance | Confirm signature verification blocks forged requests |
| Set all env vars in Vercel | Confirm signature verification blocks forged requests |
| Write `main.py` — FastAPI app | |
| Write `api/index.py` — Vercel entry point | |
| Write `src/db/client.py` — Motor connection | |
| Write `src/db/queries.py` — all query functions | |
| Write `src/lib/config.py` — Pydantic Settings | |
| Write `src/lib/redis_client.py` — Upstash connection | |
| Write `src/handlers/twilio.py` — parse form body | |
| Write `src/services/twilio.py` — verify signature + send | |
| Run seed.py to populate demo seller + product | |
| Configure Twilio webhook URL → `/api/webhooks/twilio` | |

**Day 1 Exit Condition:** WhatsApp message → Twilio webhook → Vercel → FastAPI logs parsed From, To, Body fields. Signature verification blocks forged requests. `git tag v0.1-webhook-working`

### 7.2 Day 2 — Full Buyer Conversation Loop

**Goal:** Buyer texts → browses catalog → selects product → confirms quantity → gives address → receives order summary with static bank placeholder. Order document in MongoDB.

| Build | Test |
|-------|------|
| Write `src/bot/scripts.py` — all SCRIPTS keys | Test "Hi" → receive catalog |
| Write `src/bot/intent.py` — classify_intent() | Test "1" in browse state → receive product detail |
| Write `src/services/state.py` — process_message() | Test "1" (Buy now) → receive "How many?" |
| Write handle_idle() — buyer receives catalog | Test "3" quantity → receive cart summary |
| Write handle_browse() — product selected by number | Test "CONFIRM" → receive delivery address prompt |
| Write handle_select() — Buy now flows to cart | Type address → receive order summary with static bank placeholder |
| Write handle_cart() — quantity, cart summary | Check orders collection in MongoDB — document exists with status "pending" |
| Write handle_checkout() — CONFIRM → delivery | Check conversations collection — state is "confirm" |
| Write handle_delivery() — address, order created | Run full loop 3 times end to end |
| Write handle_confirm() — PAID acknowledged | |

**Day 2 Exit Condition:** Full buyer conversation works end to end. Order document in MongoDB. State machine handles every transition without crashing. `git tag v0.2-buyer-loop-working`

### 7.3 Day 3 — Seller Commands + Nomba + Deploy + Demo

**Goal:** Complete loop — seller onboards, Nomba virtual account created, buyer orders, payment webhook fires, both phones notified. Deployed to Vercel.

| Build | Test |
|-------|------|
| Write seller commands — MENU, VIEW ORDERS, CHECK BALANCE, PAUSE, RESUME | Text Hustaq bot: "I want to sell" → complete full onboarding |
| Write seller onboarding conversation | Confirm seller document in MongoDB has all fields populated |
| Write product add flow — photo → name → price | Confirm Nomba virtual account created |
| Write `src/services/nomba.py` — get_token + create_virtual_account | Run complete buyer loop with real Nomba bank details |
| Wire real bank details into handle_delivery() | Fire Nomba webhook with curl — confirm both phones notified |
| Write `src/handlers/nomba.py` — payment.success handler | Fire same webhook again — confirm idempotency |
| Wire dual notifications: buyer + seller on payment | Test PAUSE → buyer texts → bot silent → RESUME → bot replies |
| Deploy: `vercel --prod` | Run entire demo loop 3 times clean |
| Twilio webhook updated to prod Vercel URL | Write docs/DEMO_SCRIPT.md |
| | `git tag v1.0-demo-ready` |

**Day 3 Exit Condition:** Full 6-step demo loop runs 3 times clean. Deployed to Vercel. Nomba idempotency confirmed. `docs/DEMO_SCRIPT.md` written. `git tag v1.0-demo-ready`

---

## 8. Environment Variables Reference

| Variable | Source | Value / Notes |
|----------|--------|---------------|
| `MONGODB_URI` | Vercel env var | `mongodb+srv://<user>:<pass>@cluster.mongodb.net/hustaq` |
| `UPSTASH_REDIS_URL` | Vercel env var | `redis://default:xxxx@xxx.upstash.io:6379` |
| `TWILIO_ACCOUNT_SID` | Vercel env var | Twilio console → Dashboard → Account SID |
| `TWILIO_AUTH_TOKEN` | Vercel env var | Twilio console → Dashboard → Auth Token |
| `TWILIO_WHATSAPP_NUMBER` | Vercel env var | `whatsapp:+234...` format — your approved sender |
| `NOMBA_CLIENT_ID` | Vercel env var | Nomba sandbox client_id |
| `NOMBA_CLIENT_SECRET` | Vercel env var | Nomba sandbox client_secret |
| `NOMBA_ENV` | Vercel env var | `sandbox` for hackathon, `prod` after |
| `VERCEL_URL` | Vercel (auto-set) | Your deployment URL — used for Nomba callback |

---

## 9. Full Build Checklist

Work through in order. Each item is a commit point.

| # | Task | Day | Notes |
|---|------|-----|-------|
| ☐ | MongoDB Atlas M0 cluster created. Connection string noted. | 1 | |
| ☐ | Upstash Redis instance created. Connection URL noted. | 1 | |
| ☐ | Vercel project created. GitHub repo connected. | 1 | |
| ☐ | All env vars set in Vercel. | 1 | See Section 8 |
| ☐ | `main.py` — FastAPI app with routers | 1 | |
| ☐ | `api/index.py` — Vercel entry point | 1 | |
| ☐ | `src/db/client.py` — Motor connection singleton | 1 | |
| ☐ | `src/db/queries.py` — all CRUD functions | 1 | |
| ☐ | `src/lib/config.py` — Pydantic Settings | 1 | |
| ☐ | `src/handlers/twilio.py` — form body parsed, logged | 1 | |
| ☐ | `src/services/twilio.py` — verify + send working | 1 | |
| ☐ | `verify_twilio_signature()` — valid passes, forged returns 403 | 1 | |
| ☐ | Seed script run — demo seller + product in MongoDB | 1 | |
| ☐ | Twilio webhook URL → Vercel `/api/webhooks/twilio` | 1 | Method: POST |
| ☐ | WhatsApp message → Vercel logs show parsed fields | 1 | Day 1 exit |
| ☐ | `src/bot/scripts.py` — all SCRIPTS keys written | 2 | |
| ☐ | `src/bot/intent.py` — classify_intent() all patterns | 2 | |
| ☐ | `src/services/state.py` — process_message() routes correctly | 2 | |
| ☐ | handle_idle() — buyer receives catalog | 2 | Test "Hi" |
| ☐ | handle_browse() — product selected by number | 2 | Test "1" |
| ☐ | handle_select() — Buy now → cart | 2 | Test "1" |
| ☐ | handle_cart() — quantity → cart summary | 2 | Test "3" |
| ☐ | handle_checkout() — CONFIRM → delivery | 2 | Test "CONFIRM" |
| ☐ | handle_delivery() — order created in MongoDB | 2 | Check orders collection |
| ☐ | handle_confirm() — PAID acknowledged | 2 | |
| ☐ | Full buyer loop 3 times clean | 2 | Day 2 exit |
| ☐ | Seller MENU, VIEW ORDERS, CHECK BALANCE, PAUSE, RESUME | 3 | |
| ☐ | Seller onboarding — WELCOME to DONE | 3 | |
| ☐ | Product add flow — photo → name → price → saved | 3 | |
| ☐ | `src/services/nomba.py` — token + virtual account | 3 | |
| ☐ | Real bank details in handle_delivery() | 3 | |
| ☐ | `src/handlers/nomba.py` — payment.success handler | 3 | Curl test |
| ☐ | Idempotency — same webhook twice, processes once | 3 | |
| ☐ | Dual notifications — buyer + seller | 3 | |
| ☐ | `vercel --prod` — deployed | 3 | |
| ☐ | Twilio webhook updated to prod Vercel URL | 3 | |
| ☐ | Full demo loop — 3 clean runs | 3 | Day 3 exit |
| ☐ | `docs/DEMO_SCRIPT.md` written | 3 | |

---

## 10. Demo Day Checklist

| Task | Notes |
|------|-------|
| ☐ Vercel deployment healthy — GET `/api/health` returns 200 | |
| ☐ MongoDB live — sellers collection has demo seller | |
| ☐ Redis live — `get_redis().ping()` returns True | |
| ☐ Twilio sender active — send test message from Twilio console | |
| ☐ Nomba token resolves — `get_nomba_token()` returns a token | |
| ☐ Demo seller has `nomba_virtual_account` populated | |
| ☐ Vercel function logs accessible | |
| ☐ Full demo loop dry run completed in last 2 hours | All 6 steps must pass |
| ☐ Nomba curl command ready to paste in terminal | Judges love seeing this |
| ☐ `docs/DEMO_SCRIPT.md` open with exact messages in order | |
| ☐ Demo video backed up to Google Drive | Fallback if live demo fails |

### Demo Loop — 6 Steps, Say Each One Aloud

1. Text Hustaq bot number: "I want to sell" → complete onboarding → shop is live
2. Text seller's Twilio number as buyer: "Hi" → receive catalog
3. Reply "1" → product detail → "1" Buy → quantity → cart summary
4. Reply CONFIRM → type address → receive order summary with real Nomba bank details
5. Run curl command in terminal (visible to judges) → fire Nomba payment.success
6. Both phones receive notification simultaneously. Demo done.

---

**Python. FastAPI. MongoDB. Vercel. Ship it.**
