const API_BASE = window.PRECO_UNICO_API || "https://preco-unico-api.onrender.com";
let products = [];
let category = "Todos";
let query = "";
let saved = JSON.parse(localStorage.getItem("pu-saved") || "[]");
let savedMode = false;
let apiMessage = "Carregando ofertas reais…";
const $ = (s) => document.querySelector(s);
const money = (cents) => (Number(cents || 0) / 100).toLocaleString("pt-BR", { style:"currency", currency:"BRL" });
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
  if (sort === "low") list.sort((a,b) => (a.priceCents + (a.shippingCents || 0)) - (b.priceCents + (b.shippingCents || 0)));
  if (sort === "high") list.sort((a,b) => b.priceCents - a.priceCents);
  if (sort === "name") list.sort((a,b) => a.title.localeCompare(b.title, "pt-BR"));
  return list;
}
function render() {
  const list = visible();
  $("#resultsCount").textContent = list.length + (list.length === 1 ? " oferta encontrada" : " ofertas encontradas");
  $("#savedCount").textContent = saved.length;
  $("#productGrid").innerHTML = list.map(p => {
    const isSaved = saved.includes(String(p.id)) || saved.includes(p.id);
    const shipping = p.shippingCents === null || p.shippingCents === undefined ? "Frete a consultar" :
      (p.shippingCents === 0 ? "Frete grátis informado" : "Frete " + money(p.shippingCents));
    const updated = p.updatedAt ? new Date(p.updatedAt).toLocaleDateString("pt-BR") : "Data não informada";
    return `<article class="product-card">
      <div class="product-visual">
        <span class="tag ${p.isOriginal ? "" : "alt"}">${p.isOriginal ? "ORIGINAL INFORMADO" : "OFERTA DO PARCEIRO"}</span>
        <button class="save ${isSaved ? "saved" : ""}" data-save="${escapeHtml(p.id)}" aria-label="Salvar produto">${isSaved ? "♥" : "♡"}</button>
        <span class="emoji">🛍️</span>
      </div>
      <div class="product-info">
        <div class="product-type">${escapeHtml(p.category)} · ${escapeHtml(p.condition || "Condição não informada")}</div>
        <h3>${escapeHtml(p.title)}</h3>
        <div class="product-sub">${escapeHtml(p.merchant)} · ${escapeHtml(p.partner)}</div>
        <div class="price-row"><div><div class="price">${money(p.priceCents)}</div><div class="price-note">${shipping}</div></div></div>
        <div class="price-note">Atualizado: ${escapeHtml(updated)}</div>
        <button class="compare-btn" data-detail="${escapeHtml(p.id)}">Ver oferta e condições →</button>
      </div>
    </article>`;
  }).join("");
  $("#emptyState").hidden = list.length > 0;
  $("#productGrid").hidden = list.length === 0;
  if (!list.length) {
    $("#emptyState h3").textContent = savedMode ? "Nenhum produto salvo nesta busca" : "Nenhuma oferta real disponível";
    $("#emptyState p").textContent = apiMessage;
  }
}
function detail(id) {
  const p = products.find(x => String(x.id) === String(id));
  if (!p) return;
  const shipping = p.shippingCents === null || p.shippingCents === undefined ? "Consulte o frete na loja" :
    (p.shippingCents === 0 ? "Frete grátis informado pela fonte" : money(p.shippingCents));
  const updated = p.updatedAt ? new Date(p.updatedAt).toLocaleString("pt-BR") : "Não informado";
  $("#dialogContent").innerHTML = `
    <div class="eyebrow dark">OFERTA DE PARCEIRO</div>
    <div class="dialog-emoji">🛍️</div>
    <h2>${escapeHtml(p.title)}</h2>
    <p style="color:#718096;font-size:12px;line-height:1.7">${escapeHtml(p.description || "Descrição não fornecida pela loja.")}</p>
    <div class="dialog-offer"><div><b>${escapeHtml(p.merchant)}</b><small>Fonte: ${escapeHtml(p.partner)}</small></div><b>${money(p.priceCents)}</b></div>
    <div class="dialog-offer"><div><b>Frete</b><small>Consulte condições e endereço na loja</small></div><b>${escapeHtml(shipping)}</b></div>
    <div class="dialog-offer"><div><b>Condição</b><small>${escapeHtml(p.condition || "Não informada")}</small></div><b>${p.isOriginal ? "Original informado" : "Não confirmado"}</b></div>
    <p style="font-size:10px;color:#718096">Última atualização informada: ${escapeHtml(updated)}. Preço e disponibilidade podem mudar no site do vendedor.</p>
    <button class="compare-btn" style="margin-top:18px" id="goStore">Ir à loja e consultar →</button>
    <p style="font-size:10px;color:#718096;margin-top:10px">Podemos receber comissão se você comprar por um link de parceiro, sem custo adicional informado ao comprador.</p>`;
  $("#productDialog").showModal();
  $("#goStore").addEventListener("click", () => {
    window.location.href = API_BASE + "/r/" + encodeURIComponent(p.id);
  });
}
async function loadOffers() {
  try {
    const response = await fetch(API_BASE + "/api/offers", { headers:{ "Accept":"application/json" } });
    if (!response.ok) throw new Error("API indisponível");
    const data = await response.json();
    products = Array.isArray(data.offers) ? data.offers : [];
    apiMessage = products.length ? "Compare preço, frete e condições. A compra acontece no site da loja." :
      "Estamos preparando as conexões oficiais com lojas e redes de afiliados. Não exibimos produtos fictícios.";
  } catch {
    products = [];
    apiMessage = "O serviço de ofertas está temporariamente indisponível. Tente novamente em instantes.";
  }
  render();
}
$("#searchForm").addEventListener("submit", e => {
  e.preventDefault(); query = $("#searchInput").value.trim(); savedMode = false; render();
  $("#ofertas").scrollIntoView({ behavior:"smooth" });
});
$("#searchInput").addEventListener("input", e => { query = e.target.value.trim(); savedMode = false; render(); });
$("#categoryList").addEventListener("click", e => {
  const button = e.target.closest("[data-category]");
  if (!button) return;
  category = button.dataset.category;
  document.querySelectorAll(".chip").forEach(x => x.classList.toggle("active", x === button));
  render();
});
$("#sortSelect").addEventListener("change", render);
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
loadOffers();
