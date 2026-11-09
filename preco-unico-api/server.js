import express from "express";
import cors from "cors";
import helmet from "helmet";
import rateLimit from "express-rate-limit";
import pg from "pg";
import { timingSafeEqual } from "node:crypto";
import { hostAllowed, isValidHttpUrl, safeStatus, validateOffer } from "./lib.js";

const { Pool } = pg;
const app = express();
const PORT = Number(process.env.PORT || 3000);
const DATABASE_URL = process.env.DATABASE_URL;
const ADMIN_API_KEY = process.env.ADMIN_API_KEY || "";
const ALLOWED_HOSTS = (process.env.AFFILIATE_ALLOWED_HOSTS || "").split(",").map(x => x.trim()).filter(Boolean);
const FRONTEND_ORIGIN = process.env.FRONTEND_ORIGIN || "https://preco-unico.onrender.com";
const pool = DATABASE_URL ? new Pool({
  connectionString: DATABASE_URL,
  ssl: process.env.PGSSLMODE === "disable" ? false : { rejectUnauthorized: false },
  max: 5,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 5000
}) : null;

app.disable("x-powered-by");
// Render terminates TLS and forwards the original client IP through one trusted proxy.
app.set("trust proxy", 1);
app.use(helmet());
app.use(cors({ origin: FRONTEND_ORIGIN.split(",").map(x => x.trim()), methods:["GET","POST"], allowedHeaders:["Content-Type","Authorization"] }));
app.use(express.json({ limit:"256kb" }));
app.use("/api", rateLimit({ windowMs:60_000, limit:120, standardHeaders:"draft-7", legacyHeaders:false }));

function adminOnly(req, res, next) {
  if (!ADMIN_API_KEY) return res.status(503).json({ error:"Painel administrativo ainda não configurado." });
  const supplied = (req.headers.authorization || "").replace(/^Bearer\s+/i, "");
  const a = Buffer.from(supplied);
  const b = Buffer.from(ADMIN_API_KEY);
  if (a.length !== b.length || !timingSafeEqual(a,b)) return res.status(401).json({ error:"Não autorizado." });
  next();
}

function dbRequired(req, res, next) {
  if (!pool) return res.status(503).json({ error:"Banco de dados ainda não conectado.", code:"DATABASE_NOT_CONFIGURED" });
  next();
}

app.get("/health", async (_req, res) => {
  let database = "not_configured";
  if (pool) {
    try { await pool.query("SELECT 1"); database = "connected"; }
    catch { database = "unavailable"; }
  }
  res.status(database === "unavailable" ? 503 : 200).json({
    service:"preco-unico-api",
    status: database === "unavailable" ? "degraded" : "ok",
    database,
    affiliatePartnersConnected: false,
    updatedAt: new Date().toISOString()
  });
});

app.get("/api/status", async (_req,res) => {
  let database = "not_configured";
  if (pool) {
    try { await pool.query("SELECT 1"); database = "connected"; }
    catch { database = "unavailable"; }
  }
  res.json({
    catalog: database === "connected" ? "ready_for_authorized_feeds" : "waiting_for_database",
    database,
    affiliateNetworks: [],
    realOffersOnly: true,
    demoOffersEnabled: false
  });
});

app.get("/api/offers", async (req,res) => {
  if (!pool) return res.json({ offers:[], catalogStatus:"not_connected", message:"Nenhuma oferta real foi conectada ainda." });
  try {
    const q = String(req.query.q || "").trim().slice(0,100);
    const category = String(req.query.category || "").trim().slice(0,60);
    const result = await pool.query(
      `SELECT id, title, description, category, merchant, partner, price_cents, shipping_cents,
              currency, condition, is_original, image_url, source_updated_at, updated_at
       FROM offers
       WHERE active = TRUE AND (expires_at IS NULL OR expires_at > NOW())
         AND ($1 = '' OR title ILIKE '%' || $1 || '%' OR category ILIKE '%' || $1 || '%')
         AND ($2 = '' OR category = $2)
       ORDER BY price_cents ASC LIMIT 100`,
      [q,category]
    );
    res.json({ offers:result.rows.map(row => ({
      id:row.id,title:row.title,description:row.description,category:row.category,
      merchant:row.merchant,partner:row.partner,priceCents:Number(row.price_cents),
      shippingCents:row.shipping_cents === null ? null : Number(row.shipping_cents),
      currency:row.currency,condition:row.condition,isOriginal:row.is_original,
      imageUrl:row.image_url,sourceUpdatedAt:row.source_updated_at,updatedAt:row.updated_at
    })), catalogStatus:"connected" });
  } catch (error) {
    console.error("offers_query_failed", error.message);
    res.status(500).json({ error:"Não foi possível consultar as ofertas." });
  }
});

app.get("/api/offers/:id/history", dbRequired, async (req,res) => {
  const days = Math.min(365, Math.max(1, Number.parseInt(req.query.days || "90", 10) || 90));
  try {
    const result = await pool.query(
      `SELECT price_cents, shipping_cents, currency, captured_at
       FROM price_history
       WHERE offer_id = $1 AND captured_at >= NOW() - ($2::int * INTERVAL '1 day')
       ORDER BY captured_at ASC LIMIT 500`,
      [req.params.id, days]
    );
    res.json({ offerId:req.params.id, days, points:result.rows.map(row => ({
      priceCents:Number(row.price_cents),
      shippingCents:row.shipping_cents === null ? null : Number(row.shipping_cents),
      currency:row.currency,
      capturedAt:row.captured_at
    })) });
  } catch (error) {
    if (error.code === "42P01") return res.status(503).json({ error:"Histórico ainda não foi inicializado. Aplique a migração do banco.", code:"HISTORY_SCHEMA_MISSING" });
    console.error("price_history_failed", error.message);
    res.status(500).json({ error:"Não foi possível consultar o histórico." });
  }
});

app.get("/api/offers/compare", dbRequired, async (req,res) => {
  const ids = String(req.query.ids || "").split(",").map(x => x.trim()).filter(Boolean);
  if (ids.length < 2 || ids.length > 4 || ids.some(id => !/^\\d+$/.test(id))) {
    return res.status(400).json({ error:"Informe de 2 a 4 IDs de ofertas válidos." });
  }
  try {
    const result = await pool.query(
      `SELECT id,title,merchant,partner,price_cents,shipping_cents,currency,
              condition,is_original,availability,product_url,image_url,source_updated_at,updated_at
       FROM offers
       WHERE id = ANY($1::bigint[]) AND active = TRUE
         AND (expires_at IS NULL OR expires_at > NOW())`,
      [ids]
    );
    res.json({ offers:result.rows.map(row => ({
      id:String(row.id),title:row.title,merchant:row.merchant,partner:row.partner,
      priceCents:Number(row.price_cents),shippingCents:row.shipping_cents === null ? null : Number(row.shipping_cents),
      currency:row.currency,condition:row.condition,isOriginal:row.is_original,
      availability:row.availability,productUrl:row.product_url,imageUrl:row.image_url,
      sourceUpdatedAt:row.source_updated_at,updatedAt:row.updated_at
    })) });
  } catch (error) {
    console.error("offer_compare_failed", error.message);
    res.status(500).json({ error:"Não foi possível comparar as ofertas." });
  }
});

app.get("/r/:id", dbRequired, async (req,res) => {
  try {
    const result = await pool.query(
      "SELECT id, affiliate_url, active, expires_at FROM offers WHERE id = $1",
      [req.params.id]
    );
    const offer = result.rows[0];
    if (!offer || !offer.active || (offer.expires_at && new Date(offer.expires_at) <= new Date())) {
      return res.status(404).send("Oferta indisponível ou expirada.");
    }
    if (!isValidHttpUrl(offer.affiliate_url) || !hostAllowed(offer.affiliate_url, ALLOWED_HOSTS)) {
      return res.status(410).send("Link da oferta não está autorizado.");
    }
    await pool.query("INSERT INTO clicks (offer_id, clicked_at) VALUES ($1, NOW())", [offer.id]);
    res.redirect(302, offer.affiliate_url);
  } catch (error) {
    console.error("redirect_failed", error.message);
    res.status(500).send("Não foi possível abrir a oferta.");
  }
});

app.post("/api/admin/offers", adminOnly, dbRequired, async (req,res) => {
  const items = req.body?.offers;
  if (!Array.isArray(items) || items.length < 1 || items.length > 100) {
    return res.status(400).json({ error:"Envie entre 1 e 100 ofertas por lote." });
  }
  const invalid = items.findIndex(item => !validateOffer(item, ALLOWED_HOSTS).ok);
  if (invalid !== -1) return res.status(400).json({ error:"Oferta inválida no índice " + invalid + ".", details:validateOffer(items[invalid], ALLOWED_HOSTS).error });
  const client = await pool.connect();
  try {
    await client.query("BEGIN");
    for (const item of items) {
      const saved = await client.query(
        `INSERT INTO offers
         (external_id, partner, merchant, title, description, category, product_url, affiliate_url,
          price_cents, shipping_cents, currency, availability, condition, is_original, image_url,
          expires_at, active, source_updated_at, updated_at)
         VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,TRUE,$17,NOW())
         ON CONFLICT (partner, external_id) DO UPDATE SET
          merchant=EXCLUDED.merchant,title=EXCLUDED.title,description=EXCLUDED.description,
          category=EXCLUDED.category,product_url=EXCLUDED.product_url,affiliate_url=EXCLUDED.affiliate_url,
          price_cents=EXCLUDED.price_cents,shipping_cents=EXCLUDED.shipping_cents,currency=EXCLUDED.currency,
          availability=EXCLUDED.availability,condition=EXCLUDED.condition,is_original=EXCLUDED.is_original,
          image_url=EXCLUDED.image_url,expires_at=EXCLUDED.expires_at,active=TRUE,
          source_updated_at=EXCLUDED.source_updated_at,updated_at=NOW()
         RETURNING id,price_cents,shipping_cents,currency`,
        [String(item.externalId),item.partner,item.merchant,item.title.trim(),item.description || null,
         item.category,item.productUrl,item.affiliateUrl,item.priceCents,item.shippingCents ?? null,
         item.currency || "BRL",item.availability || "unknown",item.condition || "new",
         item.isOriginal === true,item.imageUrl || null,item.expiresAt || null,item.sourceUpdatedAt || null]
      );
      const offer = saved.rows[0];
      await client.query(
        `INSERT INTO price_history (offer_id,price_cents,shipping_cents,currency)
         SELECT $1,$2,$3,$4
         WHERE NOT EXISTS (
           SELECT 1 FROM price_history
           WHERE offer_id=$1 AND price_cents=$2
             AND shipping_cents IS NOT DISTINCT FROM $3
             AND currency=$4
             AND captured_at >= NOW() - INTERVAL '5 minutes'
         )`,
        [offer.id,offer.price_cents,offer.shipping_cents,offer.currency]
      );
    }
    await client.query("COMMIT");
    res.status(201).json({ accepted:items.length, message:"Ofertas validadas e atualizadas." });
  } catch (error) {
    await client.query("ROLLBACK");
    console.error("offer_import_failed", error.message);
    res.status(500).json({ error:"Falha ao importar ofertas." });
  } finally { client.release(); }
});

app.post("/api/admin/commissions", adminOnly, dbRequired, async (req,res) => {
  const item = req.body;
  const status = safeStatus(item?.status);
  if (!item || !item.partner || !item.externalEventId || !Number.isSafeInteger(item.amountCents) ||
      item.amountCents < 0 || !status) {
    return res.status(400).json({ error:"Evento de comissão inválido." });
  }
  try {
    const result = await pool.query(
      `INSERT INTO commissions (partner, external_event_id, amount_cents, currency, status, occurred_at)
       VALUES ($1,$2,$3,$4,$5,$6)
       ON CONFLICT (partner, external_event_id) DO UPDATE SET
        amount_cents=EXCLUDED.amount_cents,currency=EXCLUDED.currency,status=EXCLUDED.status,
        occurred_at=EXCLUDED.occurred_at,updated_at=NOW()
       RETURNING id`,
      [item.partner,item.externalEventId,item.amountCents,item.currency || "BRL",status,item.occurredAt || new Date().toISOString()]
    );
    res.status(201).json({ recorded:true, id:result.rows[0].id, status });
  } catch (error) {
    console.error("commission_record_failed", error.message);
    res.status(500).json({ error:"Não foi possível registrar a comissão." });
  }
});

app.get("/api/admin/summary", adminOnly, dbRequired, async (_req,res) => {
  try {
    const [clicks, commissions] = await Promise.all([
      pool.query("SELECT COUNT(*)::int AS total FROM clicks"),
      pool.query("SELECT status, COUNT(*)::int AS events, COALESCE(SUM(amount_cents),0)::bigint AS amount_cents FROM commissions GROUP BY status")
    ]);
    res.json({ clicks:clicks.rows[0].total, commissions:commissions.rows });
  } catch (error) {
    console.error("summary_failed", error.message);
    res.status(500).json({ error:"Não foi possível carregar o resumo." });
  }
});

app.use((req,res) => res.status(404).json({ error:"Rota não encontrada." }));
app.listen(PORT, () => console.log("preco-unico-api listening on " + PORT));

process.on("SIGTERM", async () => {
  if (pool) await pool.end();
  process.exit(0);
});
