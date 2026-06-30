HUSTAQ — Python Edition
WhatsApp-native commerce platform for Nigerian informal sellers.
Tech Stack: Python 3.12 · FastAPI · Mangum · AWS Lambda · RDS PostgreSQL · ElastiCache Redis · S3 · Twilio WhatsApp · Nomba Payments
Table of Contents
Product Overview & Core Demo Loop
Full Tech Stack
AWS Architecture Overview
GitHub Repository Structure
Python vs Node.js — What Changed, What Stayed
Phase 1 Build — Core App Without Nomba
6.1 AWS Infrastructure Setup
6.2 Database Schema & Seed Data
6.3 Project Scaffold & Dependencies
6.4 Lib Layer — Redis, Secrets, DB
6.5 Twilio Webhook Handler
6.6 Twilio Send Service
6.7 Bot Scripts Map
6.8 Intent Classifier
6.9 State Machine
6.10 Seller Commands & Onboarding
6.11 Serverless Deploy Config
Phase 2 — Nomba Integration
3-Day Build Flow
8.1 Day 1 — Infrastructure + Entry Points
8.2 Day 2 — Full Buyer Conversation Loop
8.3 Day 3 — Seller Commands + Nomba + Deploy + Demo
Environment Variables Reference
Agent Prompts for Python Development
Full Build Checklist
Demo Day Checklist
1. Product Overview & Core Demo Loop
Hustaq is a WhatsApp-native commerce platform for Nigerian informal sellers. Sellers manage their entire shop by texting a WhatsApp bot number. Buyers message the seller's WhatsApp number; Hustaq intercepts those messages via Twilio, runs them through a Python state machine, and replies with product catalogs, order confirmations, and payment instructions. Payments flow through Nomba virtual accounts. When a buyer pays, Nomba fires a webhook, Hustaq confirms the order automatically, and both buyer and seller receive WhatsApp notifications — all without a website or app.
Core Demo Loop
Table
Step	Flow
1	Seller texts Hustaq bot → onboarding completes → Nomba virtual account issued
2	Buyer messages seller WhatsApp → Twilio webhook fires → Python Lambda replies with catalog
3	Buyer selects product → confirms quantity → receives order summary with bank details
4	Buyer pays to Nomba virtual account via bank transfer
5	Nomba fires payment.success webhook → Lambda confirms in under 2 seconds
6	Buyer gets receipt. Seller gets new order alert. Both via WhatsApp.
Build Strategy
Phase 1 first: build everything except Nomba. Get Twilio receiving messages, the FastAPI state machine routing correctly, the full buyer conversation working end-to-end with a static bank placeholder, and seller commands functional. Only after the full conversation loop works cleanly do you add Phase 2 — Nomba virtual accounts and the payment webhook. This means you always have a working demo, even if Nomba integration hits a snag.
2. Full Tech Stack
Table
Category	Technology / Tool	Purpose
Language	Python 3.12	Primary backend language. Type hints throughout.
Web Framework	FastAPI	HTTP routing, request parsing, dependency injection. Async-native.
Lambda Adapter	Mangum	Wraps FastAPI ASGI app into AWS Lambda handler format.
Compute	AWS Lambda	Serverless function runtime. Python 3.12, arm64, 512MB, 29s timeout.
WhatsApp Layer	Twilio WhatsApp Business	Approved sender. Inbound webhooks + outbound message sends.
Twilio SDK	twilio (Python)	Client for Twilio REST API. Sends messages, verifies signatures.
HTTP Client	httpx	Async HTTP client for Nomba API calls.
Database	AWS RDS PostgreSQL	Primary storage. 5 tables: sellers, products, orders, conversations, payments.
DB Driver	psycopg2-binary	PostgreSQL driver for Python. Synchronous, battle-tested.
Cache	AWS ElastiCache Redis	Conversation state, Nomba token cache, idempotency keys.
Redis Client	redis-py	Python Redis client. redis.Redis(host=...) connection.
File Storage	AWS S3	Product photos. Downloaded from Twilio, re-uploaded here.
AWS SDK	boto3	S3 uploads, Secrets Manager reads. Standard AWS Python SDK.
Secrets	AWS Secrets Manager	Twilio auth token, Nomba credentials. Fetched at runtime via boto3.
Monitoring	AWS CloudWatch	Lambda execution logs and error alarms.
Data Validation	Pydantic v2	Request/response models, env var parsing via BaseSettings.
Payments	Nomba API (sandbox)	Virtual account creation, payment.success webhooks.
Deploy	Serverless Framework	Lambda packaging and deploy. serverless-python-requirements plugin bundles deps.
Version Control	Git + GitHub	Source control with tagged checkpoints per phase.
Full requirements.txt
plain
fastapi==0.111.0
mangum==0.17.0
twilio==9.2.2
httpx==0.27.0
psycopg2-binary==2.9.9
redis==5.0.4
boto3==1.34.0
pydantic==2.7.0
pydantic-settings==2.3.0
python-multipart==0.0.9  # Required for FastAPI form parsing (Twilio webhooks)
3. AWS Architecture Overview
All AWS services are identical to the previous Node.js plan. Only the Lambda runtime changes from Node.js 20 to Python 3.12. Everything else — VPC, IAM, RDS, ElastiCache, S3, Secrets Manager, CloudWatch — is unchanged.
Table
Service	Resource	Purpose
Compute	AWS Lambda (Python 3.12, arm64)	Runs FastAPI + Mangum. Handles all Twilio and Nomba webhooks.
Entry Point	Lambda Function URL	Public HTTPS endpoint. Twilio and Nomba POST webhooks here.
Database	RDS PostgreSQL db.t3.micro	5-table schema. sellers, products, orders, conversations, payments.
Cache	ElastiCache Redis cache.t3.micro	Conversation state per buyer. Nomba token cache. Idempotency keys.
Storage	S3 Bucket	Product photos. Twilio MediaUrl downloaded → re-uploaded to S3.
Secrets	Secrets Manager	hustaq/twilio/auth_token, hustaq/nomba/client_id, hustaq/nomba/client_secret
Monitoring	CloudWatch	Lambda execution logs. Error alarms. Log group per function.
Permissions	IAM Role (Lambda)	RDS, ElastiCache, S3, SecretsManager, CloudWatch access.
Networking	Default VPC	Lambda, RDS, ElastiCache in same VPC. No NAT gateway needed.
Request Flow
plain
Twilio / Nomba
    |
    | POST (webhook)
    v
Lambda Function URL (/webhooks/twilio or /webhooks/nomba)
    |
    v
Mangum (converts Lambda event → ASGI scope)
    |
    v
FastAPI router (src/handlers/twilio.py or src/handlers/nomba.py)
    |
    +--------> psycopg2 ---------> RDS PostgreSQL
    |
    +--------> redis-py ---------> ElastiCache Redis
    |
    +--------> boto3 ---------> S3 / Secrets Manager
    |
    +--------> httpx ---------> Nomba API
    |
    +--------> twilio SDK --------> Twilio REST API --> WhatsApp
4. GitHub Repository Structure
plain
hustaq/
├── src/
│   ├── handlers/
│   │   ├── twilio.py          # FastAPI router — Twilio webhook receiver
│   │   └── nomba.py           # FastAPI router — Nomba payment webhook
│   │
│   ├── services/
│   │   ├── twilio.py          # send_message(), save_media_to_s3()
│   │   ├── nomba.py           # get_token(), create_virtual_account()
│   │   └── state.py           # process_message() — full state machine
│   │
│   ├── bot/
│   │   ├── scripts.py         # SCRIPTS dict — every buyer + seller message
│   │   ├── intent.py          # classify_intent(message, state) -> Intent
│   │   └── onboarding.py      # Seller onboarding linear conversation
│   │
│   ├── db/
│   │   ├── schema.sql         # Full 5-table PostgreSQL schema
│   │   └── queries.py         # All DB read/write functions
│   │
│   └── lib/
│       ├── redis_client.py    # ElastiCache connection singleton
│       ├── secrets.py          # Secrets Manager fetch + in-memory cache
│       └── db.py               # psycopg2 connection pool
│
├── docs/
│   ├── STATE_TRANSITIONS.md   # Every state, intent, script key
│   └── DEMO_SCRIPT.md         # Exact messages to type on demo day
│
├── main.py                     # FastAPI app + Mangum handler entry point
├── requirements.txt
├── serverless.yml
└── README.md
Solo Git Workflow
Commit after every working unit, not at end of day. feat: twilio webhook receives and logs messages is a good commit.
Never commit broken code. If something is mid-way: git stash
Tag clean states before risky changes: git tag v0.1-webhook-working
Before adding Nomba: git tag v0.2-pre-nomba — clean rollback point if Nomba breaks anything
5. Python vs Node.js — What Changed, What Stayed
Everything in the AWS layer and business logic is identical. Only the code language and framework changed. This section is a direct mapping so nothing gets missed.
Table
Component	Node.js (Old)	Python (New)
Runtime	Node.js 20.x on Lambda	Python 3.12 on Lambda
Web framework	Hono	FastAPI
Lambda adapter	hono/aws-lambda handle()	Mangum(app)
Entry point	src/index.ts exports handler	main.py exports handler = Mangum(app)
Form body parse	c.req.parseBody()	await request.form() — FastAPI built-in
Async	async/await (native)	async def + await (FastAPI native)
DB driver	pg (node-postgres)	psycopg2-binary
Redis client	ioredis	redis-py (redis.Redis)
AWS SDK	@aws-sdk/client-s3, client-secrets-manager	boto3 (covers all AWS services)
HTTP client	node-fetch	httpx (async, used for Nomba API)
Twilio SDK	twilio (npm)	twilio (pip)
Type safety	TypeScript strict mode	Python type hints + Pydantic v2
Package file	package.json + npm	requirements.txt + pip
Deploy bundler	serverless-esbuild	serverless-python-requirements
Env vars	process.env.VAR_NAME	os.environ['VAR_NAME'] or Pydantic Settings
AWS Architecture	Unchanged	Unchanged
DB Schema	Unchanged	Unchanged
State machine logic	Unchanged (same states, same intents)	Unchanged
Redis key patterns	Unchanged	Unchanged
Nomba API calls	Unchanged	Unchanged
Twilio webhook format	Unchanged	Unchanged
6. Phase 1 Build — Core App Without Nomba
Phase 1 exit condition: a buyer texts your Twilio number, sees the catalog, selects a product, confirms quantity, gives their address, and receives an order summary with a static bank placeholder. The order row exists in RDS with status 'pending'. Everything below must work before you touch Nomba.
6.1 AWS Infrastructure Setup
Table
Task	Notes
RDS PostgreSQL db.t3.micro	Default VPC. Note endpoint, port 5432, username, password.
ElastiCache Redis cache.t3.micro	Same VPC as Lambda. Note primary endpoint.
S3 bucket hustaq-products-dev	Enable public object ACL for product photo URLs.
Lambda function	Python 3.12, arm64, 512MB memory, 29s timeout.
IAM role for Lambda	Permissions: RDS, ElastiCache, S3, SecretsManagerReadWrite, CloudWatch.
Lambda Function URL	Auth: NONE. Twilio signature verification handles security. Copy the URL.
Secrets Manager entries	hustaq/twilio/auth_token → your Twilio Auth Token.
Twilio webhook config	Twilio Console → your sender → Webhook URL: {Lambda URL}/webhooks/twilio. Method: POST.
Lambda env vars	TWILIO_ACCOUNT_SID, TWILIO_WHATSAPP_NUMBER, DB_HOST, DB_PORT, DB_USER, DB_PASS, DB_NAME, REDIS_HOST, S3_BUCKET, LAMBDA_URL
6.2 Database Schema & Seed Data
sql
-- schema.sql — run once against RDS
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE sellers (
  id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  phone_number              VARCHAR(20) UNIQUE NOT NULL,
  seller_whatsapp_number    VARCHAR(20) UNIQUE,
  twilio_number             VARCHAR(30),  -- whatsapp:+234... matches Twilio 'To' field
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

-- Seed demo seller
INSERT INTO sellers (phone_number, shop_name, shop_slug, category, location, twilio_number)
VALUES ('+2348012345678', 'Amina Fabrics', 'amina-fabrics', 'fashion',
        'Yaba Lagos', 'whatsapp:+234YOURTWILIONUMBER');

-- Seed demo product
INSERT INTO products (seller_id, name, price_kobo, stock_count, photo_url)
SELECT id, 'Hollandaise Ankara', 850000, 20, 'https://placehold.co/400'
FROM sellers WHERE shop_slug = 'amina-fabrics';
6.3 Project Scaffold & Dependencies
bash
# Create project and virtual environment
mkdir hustaq && cd hustaq
python3.12 -m venv .venv
source .venv/bin/activate

# Install all dependencies
pip install fastapi mangum twilio httpx psycopg2-binary redis boto3 \
    pydantic pydantic-settings python-multipart
pip freeze > requirements.txt
Python
# main.py — FastAPI app entry point
from fastapi import FastAPI
from mangum import Mangum
from src.handlers.twilio import router as twilio_router
from src.handlers.nomba import router as nomba_router

app = FastAPI(title='Hustaq')
app.include_router(twilio_router, prefix='/webhooks')
app.include_router(nomba_router, prefix='/webhooks')

# Mangum wraps FastAPI for Lambda
handler = Mangum(app, lifespan='off')
6.4 Lib Layer — Redis, Secrets, DB
Python
# src/lib/secrets.py
import boto3, os

_cache: dict[str, str] = {}

def get_secret(key: str) -> str:
    if key in _cache:
        return _cache[key]
    client = boto3.client('secretsmanager', region_name=os.environ['AWS_REGION'])
    resp = client.get_secret_value(SecretId=key)
    _cache[key] = resp['SecretString']
    return _cache[key]
Python
# src/lib/redis_client.py
import redis, os

_client: redis.Redis | None = None

def get_redis() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.Redis(
            host=os.environ['REDIS_HOST'],
            port=int(os.environ.get('REDIS_PORT', '6379')),
            decode_responses=True
        )
    return _client
Python
# src/lib/db.py
import psycopg2, psycopg2.extras, os

_conn = None

def get_db():
    global _conn
    if _conn is None or _conn.closed:
        _conn = psycopg2.connect(
            host=os.environ['DB_HOST'],
            port=os.environ.get('DB_PORT', '5432'),
            dbname=os.environ['DB_NAME'],
            user=os.environ['DB_USER'],
            password=os.environ['DB_PASS'],
            cursor_factory=psycopg2.extras.RealDictCursor
        )
        _conn.autocommit = True
    return _conn

def query(sql: str, params: tuple = ()) -> list[dict]:
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(sql, params)
        if cur.description:
            return cur.fetchall()
        return []
6.5 Twilio Webhook Handler
Python
# src/handlers/twilio.py
from fastapi import APIRouter, Request, Response
from src.lib.secrets import get_secret
from src.lib.db import query
from src.lib.redis_client import get_redis
from src.services.state import process_message
from src.bot.scripts import SCRIPTS
from src.services.twilio import send_message, verify_twilio_signature
import os

router = APIRouter()

@router.post('/twilio')
async def twilio_webhook(request: Request):
    # 1. Parse form-encoded body (Twilio sends application/x-www-form-urlencoded)
    form = await request.form()
    params = dict(form)

    # 2. Verify Twilio signature
    auth_token = get_secret('hustaq/twilio/auth_token')
    signature = request.headers.get('X-Twilio-Signature', '')
    url = str(request.url)
    if not verify_twilio_signature(auth_token, signature, url, params):
        return Response(status_code=403)

    # 3. Extract fields
    from_phone = params['From'].replace('whatsapp:', '')   # +2348051234567
    to_phone = params['To'].replace('whatsapp:', '')         # +2348001234567
    text = params.get('Body', '')
    media_url = params.get('MediaUrl0')  # product photo if sent
    num_media = int(params.get('NumMedia', '0'))

    # 4. Echo detection — seller chatting manually from their own phone
    seller = query(
        'SELECT * FROM sellers WHERE twilio_number = %s',
        (f'whatsapp:{to_phone}',)
    )
    if seller and from_phone == seller[0]['phone_number']:
        await handle_echo(seller[0], from_phone)
        return Response(content='', status_code=200)

    # 5. Route seller bot commands (message TO Hustaq central number)
    hustaq_number = os.environ['TWILIO_WHATSAPP_NUMBER'].replace('whatsapp:', '')
    if to_phone == hustaq_number:
        from src.services.seller_commands import handle_seller_command
        await handle_seller_command(from_phone, text, media_url)
        return Response(content='', status_code=200)

    # 6. Normal buyer message — run through state machine
    await process_message(from_phone, to_phone, text, media_url)
    return Response(content='', status_code=200)

async def handle_echo(seller: dict, seller_phone: str):
    r = get_redis()
    query('UPDATE conversations SET handoff_active=TRUE WHERE seller_id=%s', (seller['id'],))
    alerted_key = f'echo:alerted:{seller["id"]}'
    if not r.get(alerted_key):
        await send_message(seller_phone, SCRIPTS['seller']['echo_pause']('your buyer'))
        r.setex(alerted_key, 1800, '1')
6.6 Twilio Send Service
Python
# src/services/twilio.py
from twilio.rest import Client
from twilio.request_validator import RequestValidator
from src.lib.secrets import get_secret
import boto3, os, httpx

_client: Client | None = None

def get_client() -> Client:
    global _client
    if _client is None:
        auth_token = get_secret('hustaq/twilio/auth_token')
        _client = Client(os.environ['TWILIO_ACCOUNT_SID'], auth_token)
    return _client

async def send_message(to: str, body: str) -> None:
    client = get_client()
    from_number = os.environ['TWILIO_WHATSAPP_NUMBER']  # whatsapp:+234...
    to_formatted = to if to.startswith('whatsapp:') else f'whatsapp:{to}'
    client.messages.create(from_=from_number, to=to_formatted, body=body)

def verify_twilio_signature(
    auth_token: str, signature: str, url: str, params: dict
) -> bool:
    validator = RequestValidator(auth_token)
    return validator.validate(url, params, signature)

async def save_media_to_s3(media_url: str, seller_id: str) -> str:
    auth_token = get_secret('hustaq/twilio/auth_token')
    account_sid = os.environ['TWILIO_ACCOUNT_SID']
    # Twilio media requires Basic Auth
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            media_url,
            auth=(account_sid, auth_token)
        )
    # Upload to S3
    s3 = boto3.client('s3')
    key = f'products/{seller_id}/{os.urandom(8).hex()}.jpg'
    bucket = os.environ['S3_BUCKET']
    s3.put_object(
        Bucket=bucket, Key=key,
        Body=resp.content,
        ContentType='image/jpeg',
        ACL='public-read'
    )
    return f'https://{bucket}.s3.amazonaws.com/{key}'
6.7 Bot Scripts Map
Python
# src/bot/scripts.py
# Every message Hustaq sends lives here. Plain text only — no markdown.

SCRIPTS = {
    'buyer': {
        'IDLE_greeting': lambda shop_name, catalog: (
            f'Hi! Welcome to {shop_name}. Here is what we have:

{catalog}

'
            'Reply a number to order!'
        ),
        'BROWSE_catalog': lambda items: '
'.join(
            f'{i+1}. {p["name"]} - N{p["price_kobo"]//100:,}'
            for i, p in enumerate(items)
        ),
        'SELECT_product': lambda name, price, stock: (
            f'{name} - N{price:,}
{stock} in stock.

'
            '1. Buy now
2. Ask a question
3. Back to catalog'
        ),
        'CART_quantity': lambda max_stock: f'How many? (Max {max_stock})',
        'CART_summary': lambda qty, price, subtotal: (
            f'{qty} x N{price:,} = N{subtotal:,}
Reply CONFIRM to proceed.'
        ),
        'CHECKOUT_address': lambda: (
            'Delivery to?
1. Type your address
2. Send your location'
        ),
        'CONFIRM_payment': lambda shop_name, bank, acct, total: (
            f'Order Summary
Total: N{total:,}

Pay to:
{shop_name}
'
            f'{bank} - {acct}

Reply PAID when you have transferred.'
        ),
        'CONFIRM_received': lambda order_num: (
            f'Payment received! Order #{order_num} confirmed.
'
            'We will notify you when it ships.'
        ),
        'CONFIRM_checking': lambda: 'Checking your payment... one moment.',
        'CANCEL_order': lambda: 'Order cancelled. Reply MENU to start again.',
        'INVALID_input': lambda: 'Sorry, I did not get that. Reply MENU to start over.',
        'HANDOFF_notify': lambda name: f'Connecting you to {name} now.',
        'OUT_OF_STOCK': lambda left: f'Only {left} left. How many would you like?',
    },
    'seller': {
        'menu': lambda shop_name: (
            f'{shop_name} - Hustaq
'
            '1. Add Product
2. View Orders
3. Check Balance
4. Settings

'
            'Reply a number.'
        ),
        'new_order': lambda num, total, phone, addr: (
            f'New order #{num} - N{total:,} - PAID
Buyer: {phone}
Address: {addr}'
        ),
        'balance': lambda avail, pending: (
            f'Available: N{avail:,}
Pending: N{pending:,} (settles in 24h)
'
            'Reply WITHDRAW to transfer.'
        ),
        'order_list': lambda orders: (
            'No orders yet!' if not orders else
            '
'.join(f'{i+1}. #{o["order_number"]} N{o["total_kobo"]//100:,} {o["status"].upper()}'
                      for i, o in enumerate(orders))
        ),
        'pause_confirmed': lambda: 'Bot paused. Reply RESUME when done.',
        'resume_confirmed': lambda: 'Bot is back on. I will handle buyers for you.',
        'echo_pause': lambda buyer: (
            f'You are chatting with {buyer}. Bot paused. Reply RESUME when done.'
        ),
        'onboarding_welcome': lambda: (
            'Welcome to Hustaq! I will answer buyers, take orders, and confirm payments.
'
            'Ready? Reply YES.'
        ),
        'onboarding_shopname': lambda: 'What is your shop name?',
        'onboarding_category': lambda: (
            'What do you sell?
1. Fashion
2. Food and Drinks
'
            '3. Beauty
4. Gadgets
5. Other'
        ),
        'onboarding_location': lambda: 'Where are you based? (e.g. Yaba Lagos)',
        'onboarding_done': lambda shop: (
            f'{shop} is live! Send a photo to add your first product.'
        ),
        'payment_ready': lambda shop, bank, acct: (
            f'Your payment account is ready.
Buyers pay to: {shop} - {bank} - {acct}'
        ),
    }
}
6.8 Intent Classifier
Python
# src/bot/intent.py
from typing import Literal

Intent = Literal[
    'BROWSE', 'SELECT', 'QUANTITY', 'CHECKOUT', 'CONFIRM',
    'CANCEL', 'GREETING', 'HANDOFF', 'TRACK', 'PAID', 'UNKNOWN'
]

PATTERNS: dict[str, list[str]] = {
    'GREETING': ['hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening', 'oya', 'sup'],
    'BROWSE': ['what', 'have', 'products', 'catalog', 'show', 'list', 'menu', 'options', 'items', 'see'],
    'SELECT': ['1', '2', '3', '4', '5', 'first', 'second', 'third', 'that one', 'this one'],
    'QUANTITY': ['how many', 'give me', 'i want', 'send me', 'order', 'yards', 'pieces', 'units', 'bags'],
    'CHECKOUT': ['buy', 'checkout', 'proceed', 'done', 'go ahead'],
    'CONFIRM': ['confirm'],
    'PAID': ['paid', 'i paid', 'i have paid', 'transferred', 'sent', 'done'],
    'CANCEL': ['cancel', 'stop', 'no', 'never mind', 'change mind', 'nope'],
    'TRACK': ['where', 'track', 'status', 'delivery', 'shipped', 'when', 'update'],
    'HANDOFF': ['speak to', 'talk to', 'call', 'human', 'agent', 'real person', 'manager', 'owner'],
}

def classify_intent(message: str, current_state: str) -> Intent:
    m = message.strip().lower()
    # State-aware overrides
    if current_state == 'browse' and m.isdigit(): return 'SELECT'
    if current_state == 'select' and m == '1': return 'CHECKOUT'
    if current_state == 'cart' and m.isdigit(): return 'QUANTITY'
    if current_state == 'confirm' and any(p in m for p in PATTERNS['PAID']): return 'PAID'
    for intent, patterns in PATTERNS.items():
        if any(p in m for p in patterns):
            return intent  # type: ignore
    return 'UNKNOWN'
6.9 State Machine
Python
# src/services/state.py
from src.bot.intent import classify_intent
from src.bot.scripts import SCRIPTS
from src.services.twilio import send_message
from src.lib.db import query
from src.lib.redis_client import get_redis
import json, os

async def process_message(
    from_phone: str, to_phone: str,
    text: str, media_url: str | None
):
    # Find seller by their Twilio-connected number
    sellers = query('SELECT * FROM sellers WHERE twilio_number=%s',
                    (f'whatsapp:{to_phone}',))
    if not sellers:
        return
    seller = sellers[0]
    if seller['bot_paused']:
        return

    # Get or create conversation
    conv = get_or_create_conv(seller['id'], to_phone, from_phone)
    if conv['handoff_active']:
        return

    intent = classify_intent(text, conv['state'])
    state = conv['state']

    if state == 'idle':      await handle_idle(seller, conv, intent, from_phone)
    elif state == 'browse':  await handle_browse(seller, conv, intent, text, from_phone)
    elif state == 'select':  await handle_select(seller, conv, intent, text, from_phone)
    elif state == 'cart':    await handle_cart(seller, conv, intent, text, from_phone)
    elif state == 'checkout': await handle_checkout(seller, conv, intent, from_phone)
    elif state == 'delivery': await handle_delivery(seller, conv, text, from_phone)
    elif state == 'confirm': await handle_confirm(seller, conv, intent, from_phone)


def get_or_create_conv(seller_id, seller_wa, buyer_phone) -> dict:
    rows = query(
        'SELECT * FROM conversations WHERE seller_whatsapp_number=%s AND buyer_phone=%s',
        (seller_wa, buyer_phone))
    if rows:
        return rows[0]
    query(
        'INSERT INTO conversations (seller_id, seller_whatsapp_number, buyer_phone) VALUES (%s, %s, %s)',
        (seller_id, seller_wa, buyer_phone))
    return query('SELECT * FROM conversations WHERE seller_whatsapp_number=%s AND buyer_phone=%s',
                 (seller_wa, buyer_phone))[0]


def update_state(conv_id, new_state: str):
    query('UPDATE conversations SET state=%s WHERE id=%s', (new_state, conv_id))


async def handle_idle(seller, conv, intent, buyer):
    products = query('SELECT * FROM products WHERE seller_id=%s AND visible=TRUE', (seller['id'],))
    catalog = SCRIPTS['buyer']['BROWSE_catalog'](products)
    update_state(conv['id'], 'browse')
    await send_message(buyer, SCRIPTS['buyer']['IDLE_greeting'](seller['shop_name'], catalog))


async def handle_browse(seller, conv, intent, text, buyer):
    if intent != 'SELECT':
        return await send_message(buyer, SCRIPTS['buyer']['INVALID_input']())
    idx = int(text.strip()) - 1
    products = query('SELECT * FROM products WHERE seller_id=%s AND visible=TRUE ORDER BY created_at',
                     (seller['id'],))
    if idx < 0 or idx >= len(products):
        return await send_message(buyer, SCRIPTS['buyer']['INVALID_input']())
    product = products[idx]
    r = get_redis()
    r.setex(f'conv:select:{conv["id"]}', 3600, json.dumps({
        'product_id': str(product['id']),
        'name': product['name'],
        'price_kobo': product['price_kobo'],
        'stock': product['stock_count'],
    }))
    update_state(conv['id'], 'select')
    await send_message(buyer, SCRIPTS['buyer']['SELECT_product'](
        product['name'], product['price_kobo'] // 100, product['stock_count']))

# handle_select, handle_cart, handle_checkout, handle_delivery, handle_confirm
# follow same pattern: read Redis state, validate intent, write DB, send reply
6.10 Seller Commands & Onboarding
Python
# src/services/seller_commands.py
from src.lib.db import query
from src.lib.redis_client import get_redis
from src.bot.scripts import SCRIPTS
from src.services.twilio import send_message

async def handle_seller_command(seller_phone: str, text: str, media_url: str | None):
    sellers = query('SELECT * FROM sellers WHERE phone_number=%s', (seller_phone,))
    if not sellers:
        # Unknown number — start onboarding
        return await start_onboarding(seller_phone)

    seller = sellers[0]
    cmd = text.strip().lower()

    if cmd in ('menu', '0'):
        await send_message(seller_phone, SCRIPTS['seller']['menu'](seller['shop_name']))
    elif cmd in ('2', 'view orders'):
        orders = query(
            'SELECT * FROM orders WHERE seller_id=%s ORDER BY created_at DESC LIMIT 5',
            (seller['id'],))
        await send_message(seller_phone, SCRIPTS['seller']['order_list'](orders))
    elif cmd in ('3', 'check balance'):
        await send_message(seller_phone, SCRIPTS['seller']['balance'](
            seller['balance_kobo'] // 100, seller['pending_balance_kobo'] // 100))
    elif cmd == 'pause':
        query('UPDATE sellers SET bot_paused=TRUE WHERE id=%s', (seller['id'],))
        await send_message(seller_phone, SCRIPTS['seller']['pause_confirmed']())
    elif cmd == 'resume':
        query('UPDATE sellers SET bot_paused=FALSE WHERE id=%s', (seller['id'],))
        query('UPDATE conversations SET handoff_active=FALSE WHERE seller_id=%s', (seller['id'],))
        await send_message(seller_phone, SCRIPTS['seller']['resume_confirmed']())
    elif media_url:
        # Seller sent a photo — product add flow
        await handle_product_photo(seller, seller_phone, media_url)
    else:
        await send_message(seller_phone, SCRIPTS['seller']['menu'](seller['shop_name']))


async def start_onboarding(seller_phone: str):
    # Insert bare seller record, set state to onboarding in Redis
    query(
        'INSERT INTO sellers (phone_number, shop_name, shop_slug) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING',
        (seller_phone, 'New Shop', f'shop-{seller_phone[-4:]}'))
    r = get_redis()
    r.setex(f'onboard:{seller_phone}', 3600, 'WELCOME')
    await send_message(seller_phone, SCRIPTS['seller']['onboarding_welcome']())
6.11 Serverless Deploy Config
yaml
# serverless.yml
service: hustaq

provider:
  name: aws
  runtime: python3.12
  architecture: arm64
  region: eu-west-1
  memorySize: 512
  timeout: 29
  environment:
    TWILIO_ACCOUNT_SID: ${env:TWILIO_ACCOUNT_SID}
    TWILIO_WHATSAPP_NUMBER: ${env:TWILIO_WHATSAPP_NUMBER}
    DB_HOST: ${env:DB_HOST}
    DB_PORT: '5432'
    DB_NAME: hustaq
    DB_USER: ${env:DB_USER}
    DB_PASS: ${env:DB_PASS}
    REDIS_HOST: ${env:REDIS_HOST}
    S3_BUCKET: ${env:S3_BUCKET}
    LAMBDA_URL: ${env:LAMBDA_URL}
    AWS_REGION: eu-west-1
    NOMBA_ENV: sandbox

functions:
  api:
    handler: main.handler
    url: true
    events: []

plugins:
  - serverless-python-requirements

custom:
  pythonRequirements:
    dockerizePip: true  # Builds psycopg2 for Lambda Linux environment
    slim: true

# Deploy command:
# npx serverless deploy
7. Phase 2 — Nomba Integration
Start Phase 2 only after the Phase 1 exit condition passes cleanly. Add Nomba in this exact order — each step builds on the previous one.
Step 1: Nomba token service
Create src/services/nomba.py. Write get_nomba_token() using httpx to POST /auth/token/issue with grant_type=client_credentials. Cache the token in Redis as 'nomba:token' with 3500s TTL. Nomba credentials come from Secrets Manager: hustaq/nomba/client_id and hustaq/nomba/client_secret. Sandbox base URL: https://api.sandbox.nomba.com/v1
Step 2: Virtual account creation
Write create_virtual_account(seller_id, shop_name) in src/services/nomba.py. POST /accounts/virtual with accountName, currency='NGN', accountRef=seller_id, callbackUrl=LAMBDA_URL+'/webhooks/nomba'. On success update sellers table: nomba_virtual_account, nomba_bank_name, nomba_bank_code. Call this at the end of seller onboarding after location is saved.
Step 3: Real bank details in order summary
In handle_delivery() inside state.py, replace the static bank placeholder with the seller's real nomba_virtual_account and nomba_bank_name from the sellers table. SCRIPTS['buyer']['CONFIRM_payment'] already accepts these as arguments.
Step 4: Nomba payment.success webhook handler
Create src/handlers/nomba.py with a FastAPI POST /nomba route. On payment.success: check Redis key 'nomba:processed:{reference}' — skip if exists. Set key with 86400s TTL. Update orders.status='paid', payments.status='success'. Add amount to sellers.balance_kobo. Call send_message() twice: buyer receipt + seller order alert. Return 200.
Step 5: Git tag + full loop test
git tag v1.0-nomba-integrated. Run complete demo: seller onboards → virtual account created → buyer orders → curl the Nomba webhook → both phones receive notification. Check CloudWatch logs for the full execution trace.
Nomba Webhook Test Command
bash
# Simulate Nomba payment.success to test your handler
# Replace ORDER_UUID with a real order ID from your DB
curl -X POST https://your-lambda-url/webhooks/nomba \
  -H 'Content-Type: application/json' \
  -d '{
    "event": "payment.success",
    "data": {
      "reference": "NOM-TEST-001",
      "orderId": "ORDER_UUID",
      "amount": "27000",
      "status": "success",
      "customer": { "name": "Chijioke", "phone": "+2348051234567" }
    }
  }'
8. 3-Day Build Flow
Every day has a clear exit condition. Do not move to the next day until the exit condition passes. Commit after every working unit. Tag the repo at each exit condition.
8.1 Day 1 — Infrastructure + Entry Points
Goal: A WhatsApp message fires your webhook, Lambda receives it, logs it to CloudWatch, and replies.
Table
Infrastructure	Build	Test
☐ Provision RDS PostgreSQL db.t3.micro — note endpoint	☐ mkdir hustaq, create venv, pip install all deps	☐ Deploy with serverless deploy
☐ Provision ElastiCache Redis cache.t3.micro — note endpoint	☐ Write main.py — FastAPI app + Mangum handler	☐ Send WhatsApp to Twilio number — confirm CloudWatch log appears
☐ Create S3 bucket with public-read ACL	☐ Write src/lib/db.py — psycopg2 connection + query()	☐ Confirm signature verification blocks a forged curl request
☐ Create Lambda (Python 3.12, arm64, 512MB, 29s)	☐ Write src/lib/redis_client.py — get_redis()	
☐ Attach IAM role with RDS + Redis + S3 + Secrets + CW access	☐ Write src/lib/secrets.py — get_secret()	
☐ Enable Lambda Function URL — copy the URL	☐ Write src/handlers/twilio.py — parse form body, log to CloudWatch	
☐ Store Twilio Auth Token in Secrets Manager	☐ Write verify_twilio_signature() — reject forged requests	
☐ Set all Lambda env vars		
☐ Configure Twilio webhook URL → Lambda URL + /webhooks/twilio		
☐ Run schema.sql against RDS		
☐ Seed demo seller + demo product		
Day 1 Exit Condition: WhatsApp message → Twilio webhook → Lambda → CloudWatch log shows parsed From, To, Body fields. Signature verification blocks forged requests. git tag v0.1-webhook-working
8.2 Day 2 — Full Buyer Conversation Loop
Goal: Buyer texts → browses catalog → selects product → confirms quantity → gives address → receives order summary with static bank placeholder. Order row in DB.
Table
Build	Test
☐ Write src/bot/scripts.py — all SCRIPTS keys (buyer + seller)	☐ Test 'Hi' → receive catalog
☐ Write src/bot/intent.py — classify_intent() with all patterns	☐ Test '1' in browse state → receive product detail
☐ Write src/services/twilio.py — send_message() + save_media_to_s3()	☐ Test '1' (Buy now) → receive 'How many?'
☐ Write src/services/state.py — process_message() entry point	☐ Test '3' quantity → receive cart summary with correct total
☐ Write handle_idle() — buyer receives catalog	☐ Test 'CONFIRM' → receive delivery address prompt
☐ Write handle_browse() — buyer selects product by number, stored in Redis	☐ Type address → receive order summary with static bank placeholder
☐ Write handle_select() — '1' Buy now flows to cart	☐ Check orders table in RDS — row exists with status 'pending'
☐ Write handle_cart() — quantity entered, cart summary shown	☐ Check conversations table — state is 'confirm'
☐ Write handle_checkout() — CONFIRM advances to delivery	☐ Run full loop 3 times end to end without errors
☐ Write handle_delivery() — address saved, order created in DB, static bank details shown	☐ Check CloudWatch logs for any unhandled exceptions
☐ Write handle_confirm() — PAID message acknowledged	
Day 2 Exit Condition: Full buyer conversation works end to end. Order row in DB. State machine handles every transition without crashing. git tag v0.2-buyer-loop-working
8.3 Day 3 — Seller Commands + Nomba + Deploy + Demo
Goal: Complete loop — seller onboards, Nomba virtual account created, buyer orders, payment webhook fires, both phones notified. Deployed to prod.
Table
Build	Test
☐ Write src/services/seller_commands.py — MENU, VIEW ORDERS, CHECK BALANCE, PAUSE, RESUME	☐ Text Hustaq bot number: 'I want to sell' → complete full onboarding
☐ Write seller onboarding conversation — WELCOME → SHOP_NAME → CATEGORY → LOCATION → DONE	☐ Confirm seller record in DB has all fields populated
☐ Write product add flow — photo → name → price → saved to DB	☐ Confirm Nomba virtual account created and stored in sellers table
☐ Write src/services/nomba.py — get_nomba_token() with Redis cache	☐ Run complete buyer loop with real Nomba bank details in order summary
☐ Write create_virtual_account() — POSTs to Nomba, update sellers table	☐ Fire Nomba webhook with curl — confirm both phones notified
☐ Wire real Nomba bank details into handle_delivery()	☐ Fire same webhook again — confirm idempotency prevents double processing
☐ Write src/handlers/nomba.py — payment.success handler with Redis idempotency	☐ Test PAUSE → buyer texts → bot stays silent → RESUME → bot replies again
☐ Wire dual notifications: send_message() to buyer + seller on payment	☐ Run entire demo loop 3 times clean from scratch
☐ Add Redis idempotency key check on Nomba webhook	☐ Write docs/DEMO_SCRIPT.md with exact messages in order
☐ Deploy final build: npx serverless deploy	☐ git tag v1.0-demo-ready
☐ Twilio webhook updated to prod Lambda URL	
Day 3 Exit Condition: Full 6-step demo loop runs 3 times clean. Deployed to prod Lambda URL. Nomba idempotency confirmed. docs/DEMO_SCRIPT.md written. git tag v1.0-demo-ready
9. Environment Variables Reference
Table
Variable	Source	Value / Notes
TWILIO_ACCOUNT_SID	Lambda env var	Twilio console → Dashboard → Account SID
TWILIO_WHATSAPP_NUMBER	Lambda env var	whatsapp:+234... format — your approved sender
LAMBDA_URL	Lambda env var	Your Lambda Function URL (for Nomba callbackUrl)
DB_HOST	Lambda env var	RDS endpoint hostname
DB_PORT	Lambda env var	5432
DB_USER	Lambda env var	Your RDS username
DB_PASS	Lambda env var	Your RDS password
DB_NAME	Lambda env var	hustaq
REDIS_HOST	Lambda env var	ElastiCache primary endpoint hostname
REDIS_PORT	Lambda env var	6379 (default)
S3_BUCKET	Lambda env var	hustaq-products-dev
AWS_REGION	Lambda env var	e.g. eu-west-1
NOMBA_ENV	Lambda env var	sandbox for hackathon, prod after
hustaq/twilio/auth_token	Secrets Manager	Twilio Auth Token from dashboard
hustaq/nomba/client_id	Secrets Manager	Nomba sandbox client_id
hustaq/nomba/client_secret	Secrets Manager	Nomba sandbox client_secret
10. Agent Prompts for Python Development
Use these prompts verbatim when using Claude Code or any AI coding agent. Each prompt gives the agent the full context it needs to produce correct, project-specific Python.
Prompt: FastAPI + Mangum setup
I am building Hustaq — a WhatsApp commerce platform running on AWS Lambda with Python 3.12 and FastAPI. Lambda adapter: Mangum. Entry point: main.py exports handler = Mangum(app, lifespan='off'). Project structure:
src/handlers/twilio.py — FastAPI APIRouter for Twilio webhooks
src/handlers/nomba.py — FastAPI APIRouter for Nomba webhooks
src/services/twilio.py — send_message(), save_media_to_s3(), verify_twilio_signature()
src/services/nomba.py — get_nomba_token(), create_virtual_account()
src/services/state.py — process_message() state machine
src/bot/scripts.py — SCRIPTS dict (all message strings as lambdas)
src/bot/intent.py — classify_intent(message, state) -> Intent
src/lib/db.py — psycopg2 connection + query() helper
src/lib/redis_client.py — redis.Redis singleton via get_redis()
src/lib/secrets.py — boto3 Secrets Manager fetch with in-memory cache
Help me write [SPECIFIC FILE OR FUNCTION].
Prompt: Twilio webhook handler
I am writing the Twilio webhook handler for Hustaq in src/handlers/twilio.py. Framework: FastAPI. Runtime: Python 3.12 on AWS Lambda (via Mangum). Twilio sends form-encoded POST webhooks — parse with: form = await request.form(); params = dict(form). Key fields: From (whatsapp:+234...), To, Body, NumMedia, MediaUrl0, ProfileName. Strip 'whatsapp:' prefix from From and To before any DB queries. Signature verification: use twilio.request_validator.RequestValidator(auth_token).validate(url, params, signature). Auth token comes from: get_secret('hustaq/twilio/auth_token'). Signature header: request.headers.get('X-Twilio-Signature', ''). Return Response(content='', status_code=200) immediately after dispatching to process_message(). Help me write [SPECIFIC PART].
Prompt: State machine handler
I am writing the state machine for Hustaq in src/services/state.py. Language: Python 3.12. DB: psycopg2 via query() helper. Cache: redis-py via get_redis(). Entry function: async def process_message(from_phone, to_phone, text, media_url). Conversation states in PostgreSQL table 'conversations', column 'state': idle → browse → select → cart → checkout → delivery → confirm. classify_intent(text, state) from src/bot/intent.py returns: BROWSE | SELECT | QUANTITY | CHECKOUT | CONFIRM | CANCEL | GREETING | HANDOFF | TRACK | PAID | UNKNOWN. SCRIPTS dict in src/bot/scripts.py — call like: SCRIPTS['buyer']['IDLE_greeting'](shop_name, catalog). send_message(to, body) from src/services/twilio.py sends WhatsApp replies. Redis key for selected product: conv:select:{conv_id} — JSON with product_id, name, price_kobo, stock. Redis key for cart: conv:cart:{conv_id} — JSON list of line items. Help me write [SPECIFIC STATE HANDLER].
Prompt: Nomba integration
I am adding Nomba payments to Hustaq in src/services/nomba.py. Language: Python 3.12. HTTP client: httpx (async). Cache: redis-py. Sandbox base URL: https://api.sandbox.nomba.com/v1. Auth endpoint: POST /auth/token/issue. Body: {'grant_type': 'client_credentials', 'client_id': ..., 'client_secret': ...}. Response: {'data': {'access_token': ..., 'expires_in': 3600}}. Cache token in Redis as 'nomba:token' with 3500s TTL. Virtual account endpoint: POST /accounts/virtual. Body: {'accountName': shop_name, 'currency': 'NGN', 'accountRef': seller_id, 'callbackUrl': ...}. Response: {'data': {'accountNumber': ..., 'bankName': ..., 'bankCode': ...}}. Payment success webhook body: {'event': 'payment.success', 'data': {'reference': ..., 'orderId': ..., 'amount': ..., 'customer': {'name': ..., 'phone': ...}}}. Idempotency: Redis key 'nomba:processed:{reference}' with 86400s TTL. Help me write [SPECIFIC FUNCTION].
11. Full Build Checklist
Work through in order. Each item is a commit point.
Table
#	Task	Day	Notes
☐	RDS PostgreSQL db.t3.micro provisioned. Same VPC as Lambda. Endpoint noted.	1	
☐	ElastiCache Redis cache.t3.micro provisioned. Same VPC. Endpoint noted.	1	
☐	S3 bucket created. Public-read ACL enabled.	1	
☐	Lambda function created. Python 3.12, arm64, 512MB, 29s.	1	
☐	IAM role attached with all required permissions.	1	RDS, Redis, S3, Secrets, CW
☐	Lambda Function URL enabled. URL copied.	1	This is your webhook endpoint
☐	Twilio Auth Token stored in Secrets Manager.	1	Key: hustaq/twilio/auth_token
☐	All Lambda env vars set.	1	See Section 9
☐	Twilio webhook URL configured → Lambda URL + /webhooks/twilio.	1	Method: POST
☐	schema.sql run against RDS. All 5 tables created.	1	Verify with \dt in psql
☐	Demo seller and demo product seeded.	1	SELECT * FROM sellers
☐	venv created. All pip packages installed. requirements.txt frozen.	1	
☐	main.py — FastAPI app + Mangum handler = Mangum(app, lifespan='off')	1	
☐	src/lib/db.py — psycopg2 connection + query() helper working.	1	Test with query('SELECT 1')
☐	src/lib/redis_client.py — get_redis() connects. r.ping() returns True.	1	
☐	src/lib/secrets.py — get_secret() fetches Twilio Auth Token.	1	
☐	src/handlers/twilio.py — form body parsed. Fields logged to CloudWatch.	1	
☐	verify_twilio_signature() — valid request passes. Forged request returns 403.	1	
☐	Echo detection — seller manual chat sets handoff_active=True.	1	
☐	Seller bot commands routed when 'to' == Hustaq central number.	1	
☐	src/services/twilio.py — send_message() sends real WhatsApp message.	1	Text yourself
☐	save_media_to_s3() — downloads Twilio media, uploads to S3, returns public URL.	1	Send a photo
☐	src/bot/scripts.py — all SCRIPTS keys written. No missing keys.	2	
☐	src/bot/intent.py — classify_intent() all patterns covered.	2	Test all state overrides
☐	src/services/state.py — process_message() routes to correct handler.	2	
☐	handle_idle() — buyer receives catalog on any greeting.	2	Test 'Hi'
☐	handle_browse() — product selected by number. Stored in Redis.	2	Test '1'
☐	handle_select() — Buy now flows to cart.	2	Test '1'
☐	handle_cart() — quantity entered. Cart summary with correct total shown.	2	Test '3'
☐	handle_checkout() — CONFIRM advances to delivery.	2	Test 'CONFIRM'
☐	handle_delivery() — address saved. Order created in DB. Static bank placeholder.	2	Check orders table
☐	handle_confirm() — PAID acknowledged with CONFIRM_checking.	2	
☐	Seller MENU, VIEW ORDERS, CHECK BALANCE, PAUSE, RESUME all work.	3	Text Hustaq bot number
☐	Seller onboarding — WELCOME to DONE. All steps save to DB.	3	Check sellers table after
☐	Product add flow — photo → name → price → products table row created.	3	Check products table
☐	get_nomba_token() — fetches token, caches in Redis 3500s.	3	
☐	create_virtual_account() — POSTs to Nomba, updates sellers table.	3	Check nomba_virtual_account column
☐	Real bank details wired into handle_delivery().	3	Confirm order summary shows real account
☐	Nomba payment.success handler — updates order, updates balance, sends both messages.	3	Curl test
☐	Redis idempotency — same webhook twice only processes once.	3	Send curl twice, check logs
☐	npx serverless deploy — production Lambda URL live.	3	
☐	Twilio webhook updated to prod Lambda URL.	3	
☐	Full demo loop — 3 clean runs from scratch.	3	Phase 1 + 2 complete
12. Demo Day Checklist
Table
Task	Day	Notes
☐ Lambda deployed and healthy — test POST returns 200	Demo day	
☐ RDS live — query SELECT COUNT(*) FROM sellers returns 1	Demo day	
☐ Redis live — r.ping() returns True	Demo day	
☐ Twilio sender active — send test message from Twilio console	Demo day	
☐ Nomba token resolves — get_nomba_token() returns a token	Demo day	
☐ Demo seller has nomba_virtual_account populated	Demo day	SELECT nomba_virtual_account FROM sellers
☐ CloudWatch log group streaming	Demo day	
☐ Full demo loop dry run completed in last 2 hours	Demo day	All 6 steps must pass
☐ Nomba curl command ready to paste in terminal	Demo day	Judges love seeing this
☐ docs/DEMO_SCRIPT.md open with exact messages in order	Demo day	
☐ Demo video backed up to Google Drive	Demo day	Fallback if live demo fails
Demo Loop — 6 Steps, Say Each One Aloud
Text Hustaq bot number: 'I want to sell' → complete onboarding → shop is live
Text seller's Twilio number as buyer: 'Hi' → receive catalog
Reply '1' → product detail → '1' Buy → quantity → cart summary
Reply CONFIRM → type address → receive order summary with real Nomba bank details
Run curl command in terminal (visible to judges) → fire Nomba payment.success
Both phones receive notification simultaneously. Demo done.
Python. FastAPI. AWS. Ship it.