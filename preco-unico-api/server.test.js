import test from "node:test";
import assert from "node:assert/strict";
import { hostAllowed, isValidHttpUrl, safeStatus, validateOffer } from "./lib.js";

test("accepts HTTPS product and approved affiliate links", () => {
  const offer = {
    externalId:"sku-1",partner:"partner-x",merchant:"Loja X",title:"Produto válido",
    category:"Tecnologia",productUrl:"https://loja.example/produto",
    affiliateUrl:"https://track.example/click?id=1",priceCents:12345
  };
  assert.equal(validateOffer(offer,["track.example"]).ok,true);
});

test("rejects HTTP, credentials in URL and unknown affiliate domains", () => {
  assert.equal(isValidHttpUrl("http://loja.example/item"),false);
  assert.equal(isValidHttpUrl("https://user:pass@loja.example/item"),false);
  assert.equal(hostAllowed("https://evil.example/path",["track.example"]),false);
});

test("rejects negative prices and non-authorized affiliate links", () => {
  const offer = {
    externalId:"sku-2",partner:"partner-x",merchant:"Loja X",title:"Produto válido",
    category:"Tecnologia",productUrl:"https://loja.example/produto",
    affiliateUrl:"https://track.example/click?id=1",priceCents:-1
  };
  assert.equal(validateOffer(offer,["track.example"]).ok,false);
  offer.priceCents = 100;
  assert.equal(validateOffer(offer,["other.example"]).ok,false);
});

test("only accepts known commission states", () => {
  assert.equal(safeStatus("approved"),"approved");
  assert.equal(safeStatus("paid"),"paid");
  assert.equal(safeStatus("magic"),null);
});
