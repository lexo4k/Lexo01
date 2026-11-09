import { isIP } from "node:net";

const textField = (value, min, max) =>
  typeof value === "string" && value.trim().length >= min && value.length <= max;

export function isValidHttpUrl(value) {
  try {
    const url = new URL(value);
    const host = url.hostname.toLowerCase();
    return url.protocol === "https:" &&
      !url.username && !url.password &&
      !isIP(host) &&
      host !== "localhost" &&
      !host.endsWith(".localhost") &&
      !host.endsWith(".local") &&
      !host.endsWith(".internal");
  } catch {
    return false;
  }
}

export function hostAllowed(value, allowlist = []) {
  try {
    const host = new URL(value).hostname.toLowerCase();
    return allowlist.some((entry) => {
      const domain = entry.trim().toLowerCase().replace(/^\*\./, "");
      return domain && (host === domain || host.endsWith("." + domain));
    });
  } catch {
    return false;
  }
}

export function normalizeGtin(value) {
  if (value === undefined || value === null || value === "") return null;
  const digits = String(value).replace(/[ -]/g, "");
  if (!/^\d{8}$|^\d{12}$|^\d{13}$|^\d{14}$/.test(digits)) return null;
  const body = digits.slice(0, -1);
  let sum = 0;
  for (let i = body.length - 1, weight = 3; i >= 0; i--, weight = weight === 3 ? 1 : 3) {
    sum += Number(body[i]) * weight;
  }
  const checkDigit = (10 - (sum % 10)) % 10;
  return checkDigit === Number(digits.at(-1)) ? digits : null;
}

export function sameCanonicalProduct(offers) {
  if (!Array.isArray(offers) || offers.length < 2) return false;
  const ids = offers.map(item => item.catalog_product_id ?? item.catalogProductId);
  return ids.every(id => id !== null && id !== undefined && String(id) === String(ids[0]));
}

export function validateOffer(input, allowlist = []) {
  if (!input || typeof input !== "object" || Array.isArray(input)) {
    return { ok:false, error:"Oferta inválida." };
  }
  const required = [
    ["externalId", 1, 180], ["partner", 2, 80], ["merchant", 2, 120],
    ["title", 2, 240], ["category", 2, 60]
  ];
  for (const [key, min, max] of required) {
    if (!textField(input[key], min, max)) {
      return { ok:false, error:"Campo obrigatório inválido: " + key };
    }
  }
  if (!Number.isSafeInteger(input.priceCents) || input.priceCents < 0) {
    return { ok:false, error:"Preço inválido." };
  }
  if (input.shippingCents !== undefined && input.shippingCents !== null &&
      (!Number.isSafeInteger(input.shippingCents) || input.shippingCents < 0)) {
    return { ok:false, error:"Frete inválido." };
  }
  if (!isValidHttpUrl(input.productUrl)) {
    return { ok:false, error:"URL do produto precisa ser HTTPS e pública." };
  }
  if (!isValidHttpUrl(input.affiliateUrl) || !hostAllowed(input.affiliateUrl, allowlist)) {
    return { ok:false, error:"Link de afiliado não autorizado ou domínio fora da lista permitida." };
  }
  if (input.gtin !== undefined && input.gtin !== null && input.gtin !== "" && !normalizeGtin(input.gtin)) {
    return { ok:false, error:"GTIN/EAN inválido. Informe um código de 8, 12, 13 ou 14 dígitos com dígito verificador correto." };
  }
  for (const key of ["brand", "model", "variant"]) {
    if (input[key] !== undefined && input[key] !== null &&
        (typeof input[key] !== "string" || input[key].length > 120)) {
      return { ok:false, error:"Campo de identidade inválido: " + key };
    }
  }
  if (input.description !== undefined && input.description !== null &&
      (typeof input.description !== "string" || input.description.length > 2000)) {
    return { ok:false, error:"Descrição inválida." };
  }
  if (input.imageUrl !== undefined && input.imageUrl !== null &&
      !isValidHttpUrl(input.imageUrl)) {
    return { ok:false, error:"Imagem precisa usar uma URL HTTPS pública." };
  }
  if (input.currency !== undefined && !/^[A-Z]{3}$/.test(input.currency)) {
    return { ok:false, error:"Moeda inválida. Use o código ISO de três letras." };
  }
  if (input.availability !== undefined &&
      !["unknown", "in_stock", "out_of_stock", "preorder"].includes(input.availability)) {
    return { ok:false, error:"Disponibilidade inválida." };
  }
  if (input.condition !== undefined &&
      !["new", "used", "refurbished", "open_box"].includes(input.condition)) {
    return { ok:false, error:"Condição do produto inválida." };
  }
  if (input.isOriginal !== undefined && typeof input.isOriginal !== "boolean") {
    return { ok:false, error:"Indicador de originalidade inválido." };
  }
  for (const key of ["expiresAt", "sourceUpdatedAt"]) {
    if (input[key] !== undefined && input[key] !== null &&
        (typeof input[key] !== "string" || !Number.isFinite(Date.parse(input[key])))) {
      return { ok:false, error:"Data inválida: " + key };
    }
  }
  return { ok:true };
}

export function safeStatus(value) {
  return ["estimated", "pending", "approved", "paid", "rejected"].includes(value) ? value : null;
}
