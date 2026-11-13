"""AURION Memory Wormhole: compactação sem perda e recuperação por relevância.

A compactação zlib é reversível; a seleção de contexto reduz o que é enviado
ao modelo sem apagar os registros originais. Não promete memória infinita.
"""
from __future__ import annotations

import base64
import hashlib
import re
import zlib
from typing import Any, Iterable

_WORD_RE = re.compile(r"[\wÀ-ÿ]+", re.UNICODE)


def _terms(text: str) -> set[str]:
    return {w.casefold() for w in _WORD_RE.findall(text) if len(w) > 1}


def fingerprint(text: str) -> str:
    """Identificador estável para deduplicação exata, sem alterar o original."""
    normalized = " ".join(text.split()).casefold()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def compress_text(text: str) -> dict[str, Any]:
    """Compacta texto em Base64 + zlib e informa a razão real obtida."""
    raw = text.encode("utf-8")
    packed = zlib.compress(raw, level=9)
    return {
        "codec": "zlib+base64",
        "data": base64.b64encode(packed).decode("ascii"),
        "original_bytes": len(raw),
        "compressed_bytes": len(packed),
        "ratio": round(len(packed) / len(raw), 4) if raw else 1.0,
    }


def decompress_text(payload: dict[str, Any]) -> str:
    """Restaura exatamente o texto compactado."""
    if payload.get("codec") != "zlib+base64":
        raise ValueError("Formato de memória não suportado.")
    encoded = payload.get("data")
    if not isinstance(encoded, str) or len(encoded) > 20_000_000:
        raise ValueError("Pacote de memória inválido ou grande demais.")
    try:
        packed = base64.b64decode(encoded, validate=True)
        decoder = zlib.decompressobj()
        raw = decoder.decompress(packed, 50_000_001)
        if len(raw) > 50_000_000 or decoder.unconsumed_tail:
            raise ValueError("Memória descompactada excede o limite.")
        raw += decoder.flush()
        if len(raw) > 50_000_000 or not decoder.eof:
            raise ValueError("Pacote de memória incompleto ou grande demais.")
        return raw.decode("utf-8")
    except (ValueError, zlib.error, UnicodeDecodeError) as exc:
        raise ValueError("Não foi possível restaurar a memória.") from exc


def select_relevant(
    records: Iterable[dict[str, Any]],
    query: str,
    *,
    limit: int = 12,
    max_chars: int = 9000,
) -> list[dict[str, Any]]:
    """Seleciona registros por sobreposição lexical; preserva conteúdo integral."""
    if limit < 1 or max_chars < 1:
        return []
    query_terms = _terms(query)
    if not query_terms:
        return []
    ranked: list[tuple[float, int, dict[str, Any]]] = []
    seen: set[str] = set()
    for index, original in enumerate(records):
        record = dict(original)
        content = str(record.get("content") or "")
        title = str(record.get("title") or "")
        combined = title + " " + content
        key = fingerprint(content)
        if not content.strip() or key in seen:
            continue
        seen.add(key)
        terms = _terms(combined)
        overlap = len(query_terms & terms)
        if not overlap:
            continue
        coverage = overlap / max(1, len(query_terms))
        density = overlap / max(1, len(terms))
        score = coverage * 0.75 + density * 0.25
        ranked.append((score, index, record))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    selected: list[dict[str, Any]] = []
    used = 0
    for score, _, record in ranked:
        rendered_size = len(str(record.get("title") or "")) + len(str(record.get("content") or ""))
        if selected and used + rendered_size > max_chars:
            continue
        if rendered_size > max_chars:
            continue
        record["relevance_score"] = round(score, 4)
        selected.append(record)
        used += rendered_size
        if len(selected) >= limit:
            break
    return selected


def storage_metrics(texts: Iterable[str]) -> dict[str, Any]:
    """Mede tamanho original e tamanho comprimido, sem descartar a fonte."""
    items = list(texts)
    joined = "\n".join(items)
    packed = compress_text(joined)
    return {
        "records": len(items),
        "original_bytes": packed["original_bytes"],
        "compressed_bytes": packed["compressed_bytes"],
        "ratio": packed["ratio"],
        "lossless": True,
        "note": "Compactação reversível; a taxa varia conforme o conteúdo.",
    }
