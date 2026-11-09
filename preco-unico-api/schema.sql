CREATE TABLE IF NOT EXISTS offers (
  id BIGSERIAL PRIMARY KEY,
  external_id TEXT NOT NULL,
  partner TEXT NOT NULL,
  merchant TEXT NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  category TEXT NOT NULL,
  product_url TEXT NOT NULL,
  affiliate_url TEXT NOT NULL,
  price_cents BIGINT NOT NULL CHECK (price_cents >= 0),
  shipping_cents BIGINT CHECK (shipping_cents IS NULL OR shipping_cents >= 0),
  currency CHAR(3) NOT NULL DEFAULT 'BRL',
  availability TEXT NOT NULL DEFAULT 'unknown',
  condition TEXT NOT NULL DEFAULT 'new',
  is_original BOOLEAN NOT NULL DEFAULT FALSE,
  image_url TEXT,
  expires_at TIMESTAMPTZ,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  source_updated_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (partner, external_id)
);
CREATE INDEX IF NOT EXISTS offers_active_price_idx ON offers (active, price_cents);
CREATE INDEX IF NOT EXISTS offers_category_idx ON offers (category);
CREATE TABLE IF NOT EXISTS clicks (
  id BIGSERIAL PRIMARY KEY,
  offer_id BIGINT NOT NULL REFERENCES offers(id) ON DELETE CASCADE,
  clicked_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS clicks_offer_date_idx ON clicks (offer_id, clicked_at DESC);
CREATE TABLE IF NOT EXISTS commissions (
  id BIGSERIAL PRIMARY KEY,
  partner TEXT NOT NULL,
  external_event_id TEXT NOT NULL,
  amount_cents BIGINT NOT NULL CHECK (amount_cents >= 0),
  currency CHAR(3) NOT NULL DEFAULT 'BRL',
  status TEXT NOT NULL CHECK (status IN ('estimated','pending','approved','paid','rejected')),
  occurred_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (partner, external_event_id)
);


-- Histórico de preço por oferta, com preço e frete separados.
CREATE TABLE IF NOT EXISTS price_history (
  id BIGSERIAL PRIMARY KEY,
  offer_id BIGINT NOT NULL REFERENCES offers(id) ON DELETE CASCADE,
  price_cents BIGINT NOT NULL CHECK (price_cents >= 0),
  shipping_cents BIGINT CHECK (shipping_cents IS NULL OR shipping_cents >= 0),
  currency CHAR(3) NOT NULL DEFAULT 'BRL',
  captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS price_history_offer_date_idx ON price_history (offer_id, captured_at DESC);
