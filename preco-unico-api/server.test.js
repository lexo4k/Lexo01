import test from "node:test";
import assert from "node:assert/strict";
import { hostAllowed, isValidHttpUrl, safeStatus, validateOffer } from "./lib.js";

const validOffer = () => ({
  externalId:"sku-1",partner:"partner-x",merchant:"Loja X",title:"Produto válido",
  category:"Tecnologia",productUrl:"https://loja.example/produto",
  affiliateUrl:"https://track.example/click?id=1",priceCents:12345,
  currency:"BRL",availability:"in_stock",condition:"new",isOriginal:true
});

test("accepts HTTPS product and approved affiliate links", () => {
  assert.equal(validateOffer(validOffer(),["track.example"]).ok,true);
});

test("rejects HTTP, credentials, IP and local hosts", () => {
  for (const url of [
    "http://loja.example/item",
    "https://user:pass@loja.example/item",
    "https://127.0.0.1/item",
    "https://localhost/item",
    "https://printer.local/item",
    "https://service.internal/item"
  ]) assert.equal(isValidHttpUrl(url),false);
});

test("affiliate allowlist matches exact domains and subdomains only", () => {
  assert.equal(hostAllowed("https://track.example/click",["track.example"]),true);
  assert.equal(hostAllowed("https://sub.track.example/click",["track.example"]),true);
  assert.equal(hostAllowed("https://track.example.evil.test/click",["track.example"]),false);
  assert.equal(hostAllowed("https://evil.example/click",["track.example"]),false);
});

test("rejects invalid prices, freight and unapproved affiliate links", () => {
  const offer = validOffer();
  offer.priceCents = -1;
  assert.equal(validateOffer(offer,["track.example"]).ok,false);
  offer.priceCents = 100;
  offer.shippingCents = -1;
  assert.equal(validateOffer(offer,["track.example"]).ok,false);
  delete offer.shippingCents;
  assert.equal(validateOffer(offer,["other.example"]).ok,false);
});

test("rejects malformed or oversized partner fields and metadata", () => {
  const cases = [
    { partner:" " },
    { title:"x".repeat(241) },
    { description:"x".repeat(2001) },
    { currency:"brl" },
    { availability:"maybe" },
    { condition:"unknown" },
    { isOriginal:"yes" },
    { imageUrl:"http://images.example/item.jpg" },
    { expiresAt:"not-a-date" }
  ];
  for (const patch of cases) {
    assert.equal(validateOffer({...validOffer(),...patch},["track.example"]).ok,false);
  }
  assert.equal(validateOffer([],["track.example"]).ok,false);
});

test("only accepts known commission states", () => {
  assert.equal(safeStatus("approved"),"approved");
  assert.equal(safeStatus("paid"),"paid");
  assert.equal(safeStatus("magic"),null);
});
