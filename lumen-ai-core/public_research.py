"""Pesquisa web sem chave usando resultados públicos do DuckDuckGo HTML.
Retorna links e trechos encontrados; não afirma que snippets sejam fatos verificados.
"""
from __future__ import annotations
from html.parser import HTMLParser
from urllib.parse import quote, urlparse, parse_qs, unquote
import httpx


class ResultsParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.items = []
        self._kind = None
        self._text = []
        self._href = None
        self._current = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = attrs.get("class", "").split()
        if tag == "a" and "result__a" in classes:
            self._kind = "title"
            self._text = []
            self._href = attrs.get("href", "")
        elif tag in ("a", "div", "td") and ("result__snippet" in classes or "result__body" in classes):
            self._kind = "snippet"
            self._text = []

    def handle_data(self, data):
        if self._kind:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._kind == "title":
            title = " ".join("".join(self._text).split())
            href = self._href or ""
            if href.startswith("//"):
                href = "https:" + href
            parsed = urlparse(href)
            if "duckduckgo.com" in parsed.netloc:
                target = parse_qs(parsed.query).get("uddg", [""])[0]
                if target:
                    href = unquote(target)
            if title and href.startswith("https://"):
                self._current = {"title": title, "url": href, "snippet": ""}
                self.items.append(self._current)
            self._kind = None
        elif self._kind == "snippet" and tag in ("div", "td"):
            snippet = " ".join("".join(self._text).split())
            if self.items and not self.items[-1].get("snippet"):
                self.items[-1]["snippet"] = snippet[:700]
            self._kind = None


async def search_nearby(query: str, latitude: float, longitude: float, limit: int = 8):
    """Busca locais reais próximos usando OpenStreetMap/Overpass após pedido explícito de localização."""
    import math
    import unicodedata

    normalized = unicodedata.normalize("NFKD", query).encode("ascii", "ignore").decode("ascii").lower()
    filters = None
    categories = [
        (("farmacia", "farmacias", "drogaria"), '["amenity"="pharmacy"]'),
        (("restaurante", "restaurantes", "lanchonete"), '["amenity"~"restaurant|fast_food"]'),
        (("cafe", "cafeteria"), '["amenity"="cafe"]'),
        (("mercado", "supermercado", "mercadinho"), '["shop"~"supermarket|convenience|grocery"]'),
        (("hospital", "clinica", "clinica medica"), '["amenity"~"hospital|clinic"]'),
        (("posto", "combustivel"), '["amenity"="fuel"]'),
        (("banco", "caixa eletronico"), '["amenity"~"bank|atm"]'),
        (("escola", "colegio"), '["amenity"="school"]'),
        (("hotel", "hoteis", "pousada"), '["tourism"~"hotel|guest_house"]'),
        (("parque", "praca"), '["leisure"~"park|garden"]'),
        (("academia", "ginastica"), '["leisure"="fitness_centre"]'),
    ]
    for words, tag_filter in categories:
        if any(word in normalized for word in words):
            filters = tag_filter
            break
    if filters is None:
        filters = '["name"]'
    lat = float(latitude)
    lon = float(longitude)
    query_text = (
        "[out:json][timeout:20];("
        + f"node(around:5000,{lat:.6f},{lon:.6f}){filters};"
        + f"way(around:5000,{lat:.6f},{lon:.6f}){filters};"
        + f"relation(around:5000,{lat:.6f},{lon:.6f}){filters};"
        + ");out center tags 60;"
    )
    headers = {"User-Agent": "AURION-AI/1.0 (nearby search; OpenStreetMap data)"}
    async with httpx.AsyncClient(timeout=25, follow_redirects=True, headers=headers) as client:
        response = await client.post("https://overpass-api.de/api/interpreter", data={"data": query_text})
        response.raise_for_status()
        payload = response.json()
    found = []
    seen = set()
    for element in payload.get("elements", []):
        tags = element.get("tags") or {}
        name = (tags.get("name") or "").strip()
        point = element if "lat" in element and "lon" in element else element.get("center") or {}
        if not name or "lat" not in point or "lon" not in point:
            continue
        place_lat = float(point["lat"])
        place_lon = float(point["lon"])
        key = (name.casefold(), round(place_lat, 5), round(place_lon, 5))
        if key in seen:
            continue
        seen.add(key)
        p1, p2 = math.radians(lat), math.radians(place_lat)
        dp = math.radians(place_lat - lat)
        dl = math.radians(place_lon - lon)
        hav = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
        distance_km = 6371.0 * 2 * math.asin(min(1.0, math.sqrt(hav)))
        kind = next((tags[k] for k in ("amenity", "shop", "leisure", "tourism", "office") if tags.get(k)), "local")
        address = " ".join(x for x in (tags.get("addr:street"), tags.get("addr:housenumber"), tags.get("addr:city")) if x)
        snippet = kind.replace("_", " ") + " · {:.1f} km".format(distance_km)
        if address:
            snippet += " · " + address
        map_url = "https://www.openstreetmap.org/?mlat={:.6f}&mlon={:.6f}#map=18/{:.6f}/{:.6f}".format(place_lat, place_lon, place_lat, place_lon)
        found.append({"title": name, "url": map_url, "snippet": snippet, "_distance": distance_km})
    found.sort(key=lambda item: item["_distance"])
    results = []
    for item in found[:max(1, min(limit, 10))]:
        item.pop("_distance", None)
        results.append(item)
    return results

async def search_web(query: str, limit: int = 8):
    headers = {"User-Agent": "Mozilla/5.0 (compatible; NEXORAResearch/0.1; +https://example.org)"}
    async with httpx.AsyncClient(timeout=20, follow_redirects=True, headers=headers) as client:
        response = await client.get("https://html.duckduckgo.com/html/?q=" + quote(query))
        response.raise_for_status()
    parser = ResultsParser()
    parser.feed(response.text)
    unique = []
    seen = set()
    for item in parser.items:
        if item["url"] not in seen:
            seen.add(item["url"])
            unique.append(item)
        if len(unique) >= max(1, min(limit, 10)):
            break
    if not unique:
        raise RuntimeError("O mecanismo público não retornou resultados nesta tentativa.")
    return unique
