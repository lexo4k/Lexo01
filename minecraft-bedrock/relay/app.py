"""Small authenticated relay between a Bedrock Dedicated Server and AURION.

The relay never generates dialogue. AURION remains responsible for local GGUF
inference. State is intentionally in-memory for the prototype; production
persistence and the Android bridge are separate acceptance gates.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from collections import deque
from dataclasses import dataclass, field
from threading import RLock
from typing import Deque

from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field

PAIRING_TTL_SECONDS = 300
SESSION_IDLE_TTL_SECONDS = 12 * 60 * 60
RATE_WINDOW_SECONDS = 60
RATE_LIMIT_PER_MINUTE = 30
PAIR_RATE_LIMIT_PER_MINUTE = 10
QUEUE_LIMIT = 64
EVENT_DEDUPE_LIMIT = 512
SESSION_LIMIT = 1000


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass
class Pairing:
    app_token: str
    expires_at: float


@dataclass
class Session:
    session_id: str
    app_token_hash: str
    server_token_hash: str
    created_at: float
    last_activity: float
    events: Deque[dict] = field(default_factory=lambda: deque(maxlen=QUEUE_LIMIT))
    replies: Deque[dict] = field(default_factory=lambda: deque(maxlen=QUEUE_LIMIT))
    event_ids: set[str] = field(default_factory=set)
    event_order: Deque[str] = field(default_factory=deque)
    reply_ids: set[str] = field(default_factory=set)
    request_times: dict[str, Deque[float]] = field(default_factory=dict)


class RelayStore:
    """Thread-safe, bounded prototype store. Tokens are indexed by SHA-256."""

    def __init__(self) -> None:
        self.lock = RLock()
        self.pairings: dict[str, Pairing] = {}
        self.sessions: dict[str, Session] = {}
        self.token_index: dict[str, tuple[str, str]] = {}
        self.ip_requests: dict[str, Deque[float]] = {}

    def rate_limit_ip(self, address: str, limit: int = PAIR_RATE_LIMIT_PER_MINUTE) -> None:
        now = time.monotonic()
        with self.lock:
            times = self.ip_requests.setdefault(address, deque())
            while times and now - times[0] >= RATE_WINDOW_SECONDS:
                times.popleft()
            if len(times) >= limit:
                raise HTTPException(status_code=429, detail="Muitas tentativas. Aguarde antes de tentar novamente.")
            times.append(now)

    def start_pairing(self) -> dict[str, str | int]:
        now = time.monotonic()
        code = f"{secrets.randbelow(100_000_000):08d}"
        app_token = secrets.token_urlsafe(32)
        with self.lock:
            self._purge(now)
            if len(self.pairings) >= SESSION_LIMIT:
                raise HTTPException(status_code=503, detail="Serviço ocupado. Tente novamente mais tarde.")
            self.pairings[_digest(code)] = Pairing(app_token, now + PAIRING_TTL_SECONDS)
        return {"pairing_code": code, "app_token": app_token, "expires_in": PAIRING_TTL_SECONDS}

    def claim_pairing(self, code: str) -> dict[str, str]:
        now = time.monotonic()
        key = _digest(code)
        with self.lock:
            self._purge(now)
            pairing = self.pairings.pop(key, None)
            if pairing is None or pairing.expires_at <= now:
                raise HTTPException(status_code=400, detail="Código inválido ou expirado.")
            if len(self.sessions) >= SESSION_LIMIT:
                raise HTTPException(status_code=503, detail="Limite de sessões temporárias atingido.")
            server_token = secrets.token_urlsafe(32)
            session_id = secrets.token_urlsafe(18)
            session = Session(
                session_id=session_id,
                app_token_hash=_digest(pairing.app_token),
                server_token_hash=_digest(server_token),
                created_at=now,
                last_activity=now,
            )
            self.sessions[session_id] = session
            self.token_index[session.app_token_hash] = (session_id, "app")
            self.token_index[session.server_token_hash] = (session_id, "server")
            return {"session_id": session_id, "server_token": server_token}

    def authenticate(self, authorization: str | None, side: str) -> Session:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Autorização ausente.")
        token = authorization[7:].strip()
        if len(token) < 32:
            raise HTTPException(status_code=401, detail="Credencial inválida.")
        token_hash = _digest(token)
        with self.lock:
            now = time.monotonic()
            self._purge(now)
            indexed = self.token_index.get(token_hash)
            if indexed is None or indexed[1] != side:
                raise HTTPException(status_code=401, detail="Credencial inválida.")
            session = self.sessions.get(indexed[0])
            if session is None or now - session.last_activity > SESSION_IDLE_TTL_SECONDS:
                raise HTTPException(status_code=401, detail="Sessão expirada.")
            expected = session.app_token_hash if side == "app" else session.server_token_hash
            if not hmac.compare_digest(token_hash, expected):
                raise HTTPException(status_code=401, detail="Credencial inválida.")
            session.last_activity = now
            return session

    def rate_limit(self, session: Session, side: str) -> None:
        now = time.monotonic()
        with self.lock:
            times = session.request_times.setdefault(side, deque())
            while times and now - times[0] >= RATE_WINDOW_SECONDS:
                times.popleft()
            if len(times) >= RATE_LIMIT_PER_MINUTE:
                raise HTTPException(status_code=429, detail="Limite temporário de solicitações atingido.")
            times.append(now)

    def remember_event(self, session: Session, event_id: str) -> None:
        if event_id in session.event_ids:
            raise HTTPException(status_code=409, detail="Evento duplicado.")
        if len(session.event_order) >= EVENT_DEDUPE_LIMIT:
            expired_id = session.event_order.popleft()
            session.event_ids.discard(expired_id)
        session.event_order.append(event_id)
        session.event_ids.add(event_id)

    def _purge(self, now: float) -> None:
        expired_pairings = [key for key, value in self.pairings.items() if value.expires_at <= now]
        for key in expired_pairings:
            self.pairings.pop(key, None)
        expired_sessions = [
            sid for sid, session in self.sessions.items()
            if now - session.last_activity > SESSION_IDLE_TTL_SECONDS
        ]
        for sid in expired_sessions:
            session = self.sessions.pop(sid)
            self.token_index.pop(session.app_token_hash, None)
            self.token_index.pop(session.server_token_hash, None)


class PairClaim(BaseModel):
    pairing_code: str = Field(min_length=8, max_length=8, pattern=r"^[0-9]{8}$")


class GameEvent(BaseModel):
    event_id: str = Field(min_length=8, max_length=80)
    event_type: str = Field(pattern=r"^(interaction|chat)$")
    player: str = Field(min_length=1, max_length=48)
    npc: str = Field(min_length=1, max_length=80)
    message: str = Field(default="", max_length=500)
    world_id: str = Field(default="default", min_length=1, max_length=80)


class AURIONReply(BaseModel):
    event_id: str = Field(min_length=8, max_length=80)
    message: str = Field(min_length=1, max_length=1200)
    npc: str = Field(min_length=1, max_length=80)


store = RelayStore()
app = FastAPI(title="AURION Minecraft Relay", version="0.1.0")


def _client_address(request: Request) -> str:
    # Do not trust X-Forwarded-For from arbitrary clients. Configure trusted
    # proxy handling at the hosting layer if IP-aware throttling is required.
    return request.client.host if request.client else "unknown"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "component": "aurion-minecraft-relay"}


@app.post("/v1/pair/start")
def pair_start(request: Request) -> dict[str, str | int]:
    store.rate_limit_ip(_client_address(request))
    return store.start_pairing()


@app.post("/v1/pair/claim")
def pair_claim(body: PairClaim, request: Request) -> dict[str, str]:
    store.rate_limit_ip(_client_address(request))
    return store.claim_pairing(body.pairing_code)


@app.post("/v1/server/events", status_code=202)
def server_event(body: GameEvent, authorization: str | None = Header(default=None)) -> dict[str, str]:
    session = store.authenticate(authorization, "server")
    store.rate_limit(session, "server")
    with store.lock:
        store.remember_event(session, body.event_id)
        session.events.append(body.model_dump())
    return {"accepted": body.event_id}


@app.get("/v1/app/events")
def app_events(authorization: str | None = Header(default=None)) -> dict[str, list[dict]]:
    session = store.authenticate(authorization, "app")
    store.rate_limit(session, "app")
    with store.lock:
        return {"events": list(session.events)}


@app.post("/v1/app/replies", status_code=202)
def app_reply(body: AURIONReply, authorization: str | None = Header(default=None)) -> dict[str, str]:
    session = store.authenticate(authorization, "app")
    store.rate_limit(session, "app")
    with store.lock:
        if body.event_id not in session.event_ids:
            raise HTTPException(status_code=404, detail="Evento não encontrado nesta sessão.")
        if body.event_id in session.reply_ids:
            raise HTTPException(status_code=409, detail="Resposta para este evento já registrada.")
        session.reply_ids.add(body.event_id)
        session.replies.append(body.model_dump())
    return {"accepted": body.event_id}


@app.get("/v1/server/replies")
def server_replies(authorization: str | None = Header(default=None)) -> dict[str, list[dict]]:
    session = store.authenticate(authorization, "server")
    store.rate_limit(session, "server")
    with store.lock:
        replies = list(session.replies)
        session.replies.clear()
        return {"replies": replies}
