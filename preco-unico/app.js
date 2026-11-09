const API_BASE = window.PRECO_UNICO_API || "https://preco-unico-api.onrender.com";
let products = [];
let category = "Todos";
let query = "";
let saved = JSON.parse(localStorage.getItem("pu-saved") || "[]");
let savedMode = false;
let compareIds = [];
let apiMessage = "Carregando catálogo de ofertas…";
let searchInProgress = false;
const $ = (s) => document.querySelector(s);
const money = (cents, currency = "BRL") => {
  try {
    return new Intl.NumberFormat("pt-BR", { style:"currency", currency }).format(Number(cents || 0) / 100);
  } catch {
    return (Number(cents || 0) / 100).toFixed(2) + " " + String(currency || "BRL");
  }
};
const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, ch => ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;" }[ch]));
function toast(message) {
  const el = $("#toast");
  el.textContent = message;
  el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), 2400);
}
function visible() {
  let list = products.filter(p =>
    (category === "Todos" || p.category === category) &&
    (!query || (p.title + " " + p.category + " " + p.merchant).toLowerCase().includes(query.toLowerCase())) &&
    (!$("#originalOnly").checked || p.isOriginal === true) &&
    (!$("#budgetOnly").checked || p.shippingCents !== null && p.shippingCents !== undefined) &&
    (!savedMode || saved.includes(String(p.id)) || saved.includes(p.id))
  );
  const sort = $("#sortSelect").value;
  // Valores em moedas diferentes não são comparáveis sem uma cotação cambial confiável.
  const byCurrencyThenPrice = (a,b,descending = false) => {
    const currencyA = String(a.currency || "BRL");
    const currencyB = String(b.currency || "BRL");
    if (currencyA !== currencyB) return currencyA.localeCompare(currencyB);
    const shippingKnownA = a.shippingCents !== null && a.shippingCents !== undefined;
    const shippingKnownB = b.shippingCents !== null && b.shippingCents !== undefined;
    // Não tratar frete desconhecido como grátis: ofertas com custo total conhecido vêm primeiro.
    if (shippingKnownA !== shippingKnownB) return shippingKnownA ? -1 : 1;
    const totalA = Number(a.priceCents || 0) + (shippingKnownA ? Number(a.shippingCents) : 0);
    const totalB = Number(b.priceCents || 0) + (shippingKnownB ? Number(b.shippingCents) : 0);
    return descending ? totalB - totalA : totalA - totalB;
  };
  if (sort === "low") list.sort((a,b) => byCurrencyThenPrice(a,b));
  if (sort === "high") list.sort((a,b) => byCurrencyThenPrice(a,b,true));
  if (sort === "name") list.sort((a,b) => a.title.localeCompare(b.title, "pt-BR"));
  return list;
}
function render() {
  const list = visible();
  $("#resultsCount").textContent = searchInProgress ? "Pesquisando no catálogo…" : list.length + (list.length === 1 ? " oferta encontrada" : " ofertas encontradas");
  $("#savedCount").textContent = saved.length;
  $("#productGrid").innerHTML = list.map(p => {
    const isSaved = saved.includes(String(p.id)) || saved.includes(p.id);
    const shipping = p.shippingCents === null || p.shippingCents === undefined ? "Frete a consultar" :
      (p.shippingCents === 0 ? "Frete grátis informado" : "Frete " + money(p.shippingCents, p.currency));
    const sourceUpdated = p.sourceUpdatedAt ? new Date(p.sourceUpdatedAt).toLocaleDateString("pt-BR") : null;
    const received = p.updatedAt ? new Date(p.updatedAt).toLocaleDateString("pt-BR") : null;
    const freshness = sourceUpdated ? "Fonte atualizada: " + sourceUpdated :
      received ? "Registro recebido: " + received + " (fonte sem data própria)" : "Data não informada";
    const comparing = compareIds.includes(String(p.id));
    return `<article class="product-card">
      <div class="product-visual">
        <span class="tag ${p.isOriginal ? "" : "alt"}">${p.isOriginal ? "ORIGINAL INFORMADO" : "OFERTA DO PARCEIRO"}</span>
        <button class="save ${isSaved ? "saved" : ""}" data-save="${escapeHtml(p.id)}" aria-label="Salvar produto">${isSaved ? "♥" : "♡"}</button>
        ${p.imageUrl && /^https:\/\//i.test(p.imageUrl) ? `<img class="product-image" src="${escapeHtml(p.imageUrl)}" alt="${escapeHtml(p.title)}" loading="lazy" referrerpolicy="no-referrer">` : `<span class="emoji" aria-hidden="true">🛍️</span>`}
      </div>
      <div class="product-info">
        <div class="product-type">${escapeHtml(p.category)} · ${escapeHtml(p.condition || "Condição não informada")}</div>
        <h3>${escapeHtml(p.title)}</h3>
        <div class="product-sub">${escapeHtml(p.merchant)} · ${escapeHtml(p.partner)}</div>
        <div class="price-note">${p.gtin ? "GTIN/EAN confirmado: " + escapeHtml(p.gtin) : "Identidade exata ainda não confirmada"}</div>
        <div class="price-row"><div><div class="price">${money(p.priceCents, p.currency)}</div><div class="price-note">${shipping}</div></div></div>
        <div class="price-note">${escapeHtml(freshness)}</div>
        <button class="compare-btn" data-detail="${escapeHtml(p.id)}">Ver oferta e condições →</button>
        <button class="compare-pick ${comparing ? "selected" : ""}" data-compare="${escapeHtml(p.id)}">${comparing ? "✓ Na comparação" : "＋ Comparar"}</button>
      </div>
    </article>`;
  }).join("");
  $("#compareCount").textContent = compareIds.length;
  $("#compareTray").hidden = compareIds.length === 0;
  $("#compareNow").disabled = compareIds.length < 2;
  $("#emptyState").hidden = list.length > 0;
  $("#productGrid").hidden = list.length === 0;
  if (!list.length) {
    $("#emptyState h3").textContent = savedMode ? "Nenhum produto salvo nesta busca" : query ? "Nenhuma oferta encontrada para “" + query + "”" : "Nenhuma oferta real disponível";
    $("#emptyState p").textContent = apiMessage;
  }
}
function detail(id) {
  const p = products.find(x => String(x.id) === String(id));
  if (!p) return;
  const shipping = p.shippingCents === null || p.shippingCents === undefined ? "Consulte o frete na loja" :
    (p.shippingCents === 0 ? "Frete grátis informado pela fonte" : money(p.shippingCents, p.currency));
  const sourceUpdated = p.sourceUpdatedAt ? new Date(p.sourceUpdatedAt).toLocaleString("pt-BR") : null;
  const received = p.updatedAt ? new Date(p.updatedAt).toLocaleString("pt-BR") : null;
  const freshness = sourceUpdated ? "Atualização declarada pela fonte: " + sourceUpdated :
    received ? "Registro recebido em: " + received + ". A fonte não informou a data original." : "Data não informada";
  $("#dialogContent").innerHTML = `
    <div class="eyebrow dark">OFERTA DE PARCEIRO</div>
    ${p.imageUrl && /^https:\/\//i.test(p.imageUrl) ? `<img class="dialog-image" src="${escapeHtml(p.imageUrl)}" alt="${escapeHtml(p.title)}" loading="lazy" referrerpolicy="no-referrer">` : `<div class="dialog-emoji" aria-hidden="true">🛍️</div>`}
    <h2>${escapeHtml(p.title)}</h2>\n    <div class="price-note">${p.gtin ? "GTIN/EAN: " + escapeHtml(p.gtin) : "Sem GTIN/EAN: não pode entrar em comparação de produto exato"}</div>
    <p style="color:#718096;font-size:12px;line-height:1.7">${escapeHtml(p.description || "Descrição não fornecida pela loja.")}</p>
    <div class="dialog-offer"><div><b>${escapeHtml(p.merchant)}</b><small>Fonte: ${escapeHtml(p.partner)}</small></div><b>${money(p.priceCents, p.currency)}</b></div>
    <div class="dialog-offer"><div><b>Frete</b><small>Consulte condições e endereço na loja</small></div><b>${escapeHtml(shipping)}</b></div>
    <div class="dialog-offer"><div><b>Condição</b><small>${escapeHtml(p.condition || "Não informada")}</small></div><b>${p.isOriginal ? "Original informado" : "Não confirmado"}</b></div>
    <p style="font-size:10px;color:#718096">${escapeHtml(freshness)}. Preço e disponibilidade podem mudar no site do vendedor.</p>
    <section class="history-panel" id="priceHistory"><h3>Histórico de preço</h3><p>Consultando registros disponíveis…</p></section>
    <button class="compare-btn" style="margin-top:18px" id="goStore">Ir à loja e consultar →</button>
    <p style="font-size:10px;color:#718096;margin-top:10px">Podemos receber comissão se você comprar por um link de parceiro, sem custo adicional informado ao comprador.</p>`;
  $("#productDialog").showModal();
  loadPriceHistory(p.id);
  $("#goStore").addEventListener("click", () => {
    window.location.href = API_BASE + "/r/" + encodeURIComponent(p.id);
  });
}
async function loadPriceHistory(id) {
  const panel = $("#priceHistory");
  try {
    const response = await fetch(API_BASE + "/api/offers/" + encodeURIComponent(id) + "/history?days=90");
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Histórico indisponível.");
    const points = Array.isArray(data.points) ? data.points : [];
    if (!points.length) { panel.innerHTML = "<h3>Histórico de preço</h3><p>Ainda não há capturas suficientes para mostrar a evolução.</p>"; return; }
    panel.innerHTML = "<h3>Histórico de preço (90 dias)</h3>" + points.slice(-8).reverse().map(point =>
      '<div class="history-point"><span>' + escapeHtml(new Date(point.capturedAt).toLocaleDateString("pt-BR")) + '</span><b>' +
      money(point.priceCents,point.currency) + (point.shippingCents == null ? " · frete não informado" : " · frete " + money(point.shippingCents,point.currency)) +
      '</b></div>').join("");
  } catch (error) { panel.innerHTML = "<h3>Histórico de preço</h3><p>" + escapeHtml(error.message) + "</p>"; }
}
async function compareSelected() {
  if (compareIds.length < 2) return;
  const target = $("#compareResults");
  target.hidden = false;
  target.innerHTML = "<p>Carregando comparação…</p>";
  try {
    const response = await fetch(API_BASE + "/api/offers/compare?ids=" + encodeURIComponent(compareIds.join(",")));
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Comparação indisponível.");
    const rows = Array.isArray(data.offers) ? data.offers : [];
    if (rows.length < 2) throw new Error("Não foi possível recuperar pelo menos duas ofertas ativas.");
    target.innerHTML = (data.product ? "<h3>Produto identificado: " + escapeHtml(data.product.title) + " · GTIN " + escapeHtml(data.product.gtin) + "</h3>" : "") + rows.map(p => {
      const freight = p.shippingCents == null ? "A consultar" : p.shippingCents === 0 ? "Grátis informado" : money(p.shippingCents,p.currency);
      const total = p.shippingCents == null ? "Total não calculado" : money(p.priceCents+p.shippingCents,p.currency);
      return `<article class="compare-result"><b>${escapeHtml(p.title)}</b><span>${escapeHtml(p.merchant)}</span><strong>${money(p.priceCents,p.currency)}</strong><span>Frete: ${escapeHtml(freight)}</span><strong>Total: ${escapeHtml(total)}</strong><span>Condição: ${escapeHtml(p.condition || "Não informada")}</span><span>Disponibilidade: ${escapeHtml(p.availability || "Não informada")}</span><a href="${API_BASE}/r/${encodeURIComponent(p.id)}" rel="noopener">Ver na loja →</a></article>`;
    }).join("");
  } catch (error) { target.textContent = error.message; }
}
async function loadOffers(searchTerm = query) {
  searchInProgress = true;
  render();
  try {
    const params = new URLSearchParams();
    if (searchTerm) params.set("q", searchTerm);
    if (category !== "Todos") params.set("category", category);
    const response = await fetch(API_BASE + "/api/offers" + (params.size ? "?" + params.toString() : ""), { headers:{ "Accept":"application/json" } });
    if (!response.ok) throw new Error("API indisponível");
    const data = await response.json();
    products = Array.isArray(data.offers) ? data.offers : [];
    apiMessage = products.length ? "Compare preço, frete e condições. A compra acontece no site da loja." :
      (data.message || (searchTerm ? "A pesquisa foi executada, mas não há ofertas correspondentes no catálogo conectado." : "Nenhuma oferta real foi conectada ainda."));
  } catch {
    products = [];
    apiMessage = "O serviço de ofertas está temporariamente indisponível. Tente novamente em instantes.";
  }
  searchInProgress = false;
  render();
}
$("#searchForm").addEventListener("submit", e => {
  e.preventDefault();
  query = $("#searchInput").value.trim();
  savedMode = false;
  category = "Todos";
  document.querySelectorAll(".chip").forEach(x => x.classList.toggle("active", x.dataset.category === "Todos"));
  $("#ofertas").scrollIntoView({ behavior:"smooth" });
  loadOffers(query);
});
$("#searchInput").addEventListener("input", e => { query = e.target.value.trim(); savedMode = false; });
$("#categoryList").addEventListener("click", e => {
  const button = e.target.closest("[data-category]");
  if (!button) return;
  category = button.dataset.category;
  document.querySelectorAll(".chip").forEach(x => x.classList.toggle("active", x === button));
  loadOffers(query);
});
$("#sortSelect").addEventListener("change", render);
$("#compareNow").addEventListener("click", compareSelected);
$("#clearCompare").addEventListener("click", () => { compareIds = []; $("#compareResults").hidden = true; render(); });
$("#originalOnly").addEventListener("change", () => { if ($("#originalOnly").checked) $("#budgetOnly").checked = false; render(); });
$("#budgetOnly").addEventListener("change", () => { if ($("#budgetOnly").checked) $("#originalOnly").checked = false; render(); });
$("#productGrid").addEventListener("click", e => {
  const save = e.target.closest("[data-save]");
  if (save) {
    const id = String(save.dataset.save);
    saved = saved.includes(id) ? saved.filter(x => String(x) !== id) : [...saved, id];
    localStorage.setItem("pu-saved", JSON.stringify(saved));
    render(); return;
  }
  const compare = e.target.closest("[data-compare]");
  if (compare) {
    const id = String(compare.dataset.compare);
    if (compareIds.includes(id)) compareIds = compareIds.filter(x => x !== id);
    else if (compareIds.length < 4) compareIds = [...compareIds, id];
    else toast("Compare até 4 ofertas por vez.");
    render(); return;
  }
  const button = e.target.closest("[data-detail]");
  if (button) detail(button.dataset.detail);
});
$("#savedToggle").addEventListener("click", () => {
  savedMode = !savedMode;
  $("#savedToggle").classList.toggle("active", savedMode);
  toast(savedMode ? "Mostrando produtos salvos" : "Mostrando todas as ofertas");
  render(); $("#ofertas").scrollIntoView({ behavior:"smooth" });
});
$("#dialogClose").addEventListener("click", () => $("#productDialog").close());
$("#clearFilters").addEventListener("click", () => {
  query = ""; category = "Todos"; savedMode = false;
  $("#searchInput").value = ""; $("#originalOnly").checked = false; $("#budgetOnly").checked = false;
  document.querySelectorAll(".chip").forEach(x => x.classList.toggle("active", x.dataset.category === "Todos"));
  render();
});
loadOffers("");
