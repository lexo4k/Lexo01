import { isIP } from "node:net";

export function isValidHttpUrl(value) {
  try {
    const url = new URL(value);
    return url.protocol === "https:" && !url.username && !url.password && !isIP(url.hostname);
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

export function validateOffer(input, allowlist = []) {
  if (!input || typeof input !== "object") return { ok:false, error:"Oferta inválida." };
  const required = ["externalId", "partner", "merchant", "title", "category", "productUrl", "affiliateUrl", "priceCents"];
  for (const key of required) {
    if (input[key] === undefined || input[key] === null || input[key] === "") {
      return { ok:false, error:"Campo obrigatório ausente: " + key };
    }
  }
  if (!Number.isSafeInteger(input.priceCents) || input.priceCents < 0) return { ok:false, error:"Preço inválido." };
  if (input.shippingCents !== undefined && input.shippingCents !== null &&
      (!Number.isSafeInteger(input.shippingCents) || input.shippingCents < 0)) {
    return { ok:false, error:"Frete inválido." };
  }
  if (!isValidHttpUrl(input.productUrl)) return { ok:false, error:"URL do produto precisa usar HTTPS." };
  if (!isValidHttpUrl(input.affiliateUrl) || !hostAllowed(input.affiliateUrl, allowlist)) {
    return { ok:false, error:"Link de afiliado não autorizado ou domínio fora da lista permitida." };
  }
  if (typeof input.title !== "string" || input.title.trim().length < 2 || input.title.length > 240) {
    return { ok:false, error:"Título inválido." };
  }
  if (typeof input.partner !== "string" || input.partner.length > 80 ||
      typeof input.merchant !== "string" || input.merchant.length > 120) {
    return { ok:false, error:"Identificação do parceiro ou loja inválida." };
  }
  return { ok:true };
}

export function safeStatus(value) {
  return ["estimated", "pending", "approved", "paid", "rejected"].includes(value) ? value : null;
}
