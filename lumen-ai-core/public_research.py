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
