CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS sellers (
  id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  phone_number              VARCHAR(20) UNIQUE NOT NULL,
  seller_whatsapp_number    VARCHAR(20) UNIQUE,
  twilio_number             VARCHAR(30),
  shop_name                 VARCHAR(100) NOT NULL DEFAULT 'New Shop',
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

CREATE TABLE IF NOT EXISTS products (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  seller_id     UUID REFERENCES sellers(id),
  name          VARCHAR(200) NOT NULL,
  price_kobo    BIGINT NOT NULL,
  stock_count   INTEGER DEFAULT 0,
  photo_url     VARCHAR(500),
  visible       BOOLEAN DEFAULT TRUE,
  created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS orders (
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

CREATE TABLE IF NOT EXISTS conversations (
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

CREATE TABLE IF NOT EXISTS payments (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id          UUID REFERENCES orders(id),
  seller_id         UUID REFERENCES sellers(id),
  buyer_phone       VARCHAR(20),
  amount_kobo       BIGINT NOT NULL,
  status            VARCHAR(20) DEFAULT 'pending',
  nomba_reference   VARCHAR(100) UNIQUE,
  created_at        TIMESTAMPTZ DEFAULT NOW()
);

-- Seed demo seller (safe to re-run)
INSERT INTO sellers (phone_number, shop_name, shop_slug, category, location, twilio_number)
VALUES ('+2348012345678', 'Amina Fabrics', 'amina-fabrics', 'Fashion', 'Yaba Lagos', 'whatsapp:+15005550006')
ON CONFLICT (phone_number) DO NOTHING;

-- Seed demo product
INSERT INTO products (seller_id, name, price_kobo, stock_count, photo_url)
SELECT id, 'Hollandaise Ankara', 850000, 20, 'https://placehold.co/400'
FROM sellers WHERE shop_slug = 'amina-fabrics'
ON CONFLICT DO NOTHING;
