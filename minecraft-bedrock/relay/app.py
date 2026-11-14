"""Authenticated, session-isolated relay between Bedrock Dedicated Server and AURION.

AURION remains responsible for local GGUF inference. Set
AURION_RELAY_DB_PATH to a file on persistent storage to retain pairings,
sessions, queues and rate limits across process restarts. Without that setting
the relay deliberately runs in ephemeral in-memory mode.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from threading import RLock
from typing import Iterator

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


class RelayStore:
    """SQLite-backed store with atomic writes and bounded session queues.

    SQLite coordinates concurrent requests from multiple processes. The
    configured database file must live on a persistent, private volume if
    sessions are expected to survive host replacement or machine loss.
    """

    def __init__(self, db_path: str | None = None) -> None:
        configured = db_path if db_path is not None else os.environ.get("AURION_RELAY_DB_PATH", "")
        configured = configured.strip()
        self.db_path = configured or ":memory:"
        if self.db_path != ":memory:":
            path = Path(self.db_path).expanduser()
            if not path.parent.exists():
                path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
            self.db_path = str(path)
        self.lock = RLock()
        self.connection = sqlite3.connect(
            self.db_path,
            timeout=15,
            check_same_thread=False,
            isolation_level=None,
        )
        self.connection.row_factory = sqlite3.Row
        with self.lock:
            self.connection.execute("PRAGMA foreign_keys = ON")
            self.connection.execute("PRAGMA busy_timeout = 15000")
            if self.db_path != ":memory:":
                self.connection.execute("PRAGMA journal_mode = WAL")
                self.connection.execute("PRAGMA synchronous = FULL")
            self._create_schema()
            if self.db_path != ":memory:" and os.name == "posix":
                try:
                    os.chmod(self.db_path, 0o600)
                except OSError:
                    pass

    @property
    def storage_mode(self) -> str:
        return "sqlite_file" if self.db_path != ":memory:" else "memory_ephemeral"

    def _create_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS pairings (
                code_hash TEXT PRIMARY KEY,
                app_token_hash TEXT NOT NULL,
                expires_at REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS pairings_expiry ON pairings(expires_at);

            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                app_token_hash TEXT NOT NULL UNIQUE,
                server_token_hash TEXT NOT NULL UNIQUE,
                created_at REAL NOT NULL,
                last_activity REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS sessions_activity ON sessions(last_activity);

            CREATE TABLE IF NOT EXISTS events (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
                event_id TEXT NOT NULL,
                payload TEXT NOT NULL,
                UNIQUE(session_id, event_id)
            );
            CREATE INDEX IF NOT EXISTS events_session_order ON events(session_id, sequence);

            CREATE TABLE IF NOT EXISTS event_dedupe (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
                event_id TEXT NOT NULL,
                created_at REAL NOT NULL,
                UNIQUE(session_id, event_id)
            );
            CREATE INDEX IF NOT EXISTS event_dedupe_session_order ON event_dedupe(session_id, sequence);

            CREATE TABLE IF NOT EXISTS replies (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
                event_id TEXT NOT NULL,
                payload TEXT NOT NULL,
                UNIQUE(session_id, event_id)
            );
            CREATE INDEX IF NOT EXISTS replies_session_order ON replies(session_id, sequence);

            CREATE TABLE IF NOT EXISTS reply_dedupe (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
                event_id TEXT NOT NULL,
                created_at REAL NOT NULL,
                UNIQUE(session_id, event_id)
            );
            CREATE INDEX IF NOT EXISTS reply_dedupe_session_order ON reply_dedupe(session_id, sequence);

            CREATE TABLE IF NOT EXISTS rate_limits (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                scope TEXT NOT NULL,
                rate_key TEXT NOT NULL,
                requested_at REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS rate_limits_lookup
                ON rate_limits(scope, rate_key, requested_at);
            """
        )

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        with self.lock:
            self.connection.execute("BEGIN IMMEDIATE")
            try:
                yield self.connection
            except Exception:
                self.connection.rollback()
                raise
            else:
                self.connection.commit()

    def _purge(self, connection: sqlite3.Connection, now: float) -> None:
        connection.execute("DELETE FROM pairings WHERE expires_at <= ?", (now,))
        connection.execute(
            "DELETE FROM sessions WHERE last_activity <= ?",
            (now - SESSION_IDLE_TTL_SECONDS,),
        )
        connection.execute(
            "DELETE FROM rate_limits WHERE requested_at < ?",
            (now - RATE_WINDOW_SECONDS,),
        )

    def _consume_rate(
        self,
        connection: sqlite3.Connection,
        scope: str,
        key: str,
        limit: int,
        now: float,
    ) -> None:
        connection.execute(
            "DELETE FROM rate_limits WHERE scope = ? AND rate_key = ? AND requested_at < ?",
            (scope, key, now - RATE_WINDOW_SECONDS),
        )
        count = connection.execute(
            "SELECT COUNT(*) AS amount FROM rate_limits WHERE scope = ? AND rate_key = ?",
            (scope, key),
        ).fetchone()["amount"]
        if count >= limit:
            raise HTTPException(
                status_code=429,
                detail="Muitas tentativas. Aguarde antes de tentar novamente."
                if scope == "ip"
                else "Limite temporário de solicitações atingido.",
            )
        connection.execute(
            "INSERT INTO rate_limits(scope, rate_key, requested_at) VALUES (?, ?, ?)",
            (scope, key, now),
        )

    def rate_limit_ip(self, address: str, limit: int = PAIR_RATE_LIMIT_PER_MINUTE) -> None:
        now = time.time()
        with self._transaction() as connection:
            self._purge(connection, now)
            self._consume_rate(connection, "ip", address, limit, now)

    def start_pairing(self) -> dict[str, str | int]:
        now = time.time()
        code = f"{secrets.randbelow(100_000_000):08d}"
        app_token = secrets.token_urlsafe(32)
        with self._transaction() as connection:
            self._purge(connection, now)
            count = connection.execute("SELECT COUNT(*) AS amount FROM pairings").fetchone()["amount"]
            if count >= SESSION_LIMIT:
                raise HTTPException(status_code=503, detail="Serviço ocupado. Tente novamente mais tarde.")
            connection.execute(
                "INSERT INTO pairings(code_hash, app_token_hash, expires_at) VALUES (?, ?, ?)",
                (_digest(code), _digest(app_token), now + PAIRING_TTL_SECONDS),
            )
        return {"pairing_code": code, "app_token": app_token, "expires_in": PAIRING_TTL_SECONDS}

    def claim_pairing(self, code: str) -> dict[str, str]:
        now = time.time()
        server_token = secrets.token_urlsafe(32)
        session_id = secrets.token_urlsafe(18)
        with self._transaction() as connection:
            self._purge(connection, now)
            pairing = connection.execute(
                "SELECT app_token_hash, expires_at FROM pairings WHERE code_hash = ?",
                (_digest(code),),
            ).fetchone()
            if pairing is None or pairing["expires_at"] <= now:
                raise HTTPException(status_code=400, detail="Código inválido ou expirado.")
            count = connection.execute("SELECT COUNT(*) AS amount FROM sessions").fetchone()["amount"]
            if count >= SESSION_LIMIT:
                raise HTTPException(status_code=503, detail="Limite de sessões temporárias atingido.")
            connection.execute("DELETE FROM pairings WHERE code_hash = ?", (_digest(code),))
            connection.execute(
                """
                INSERT INTO sessions(
                    session_id, app_token_hash, server_token_hash, created_at, last_activity
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (session_id, pairing["app_token_hash"], _digest(server_token), now, now),
            )
        return {"session_id": session_id, "server_token": server_token}

    def authenticate(self, authorization: str | None, side: str) -> str:
        if side not in {"app", "server"}:
            raise ValueError("Lado de autenticação inválido.")
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Autorização ausente.")
        token = authorization[7:].strip()
        if len(token) < 32:
            raise HTTPException(status_code=401, detail="Credencial inválida.")
        token_hash = _digest(token)
        token_column = "app_token_hash" if side == "app" else "server_token_hash"
        now = time.time()
        with self._transaction() as connection:
            self._purge(connection, now)
            row = connection.execute(
                f"SELECT session_id, {token_column}, last_activity FROM sessions WHERE {token_column} = ?",
                (token_hash,),
            ).fetchone()
            if row is None or now - row["last_activity"] > SESSION_IDLE_TTL_SECONDS:
                raise HTTPException(status_code=401, detail="Sessão expirada ou credencial inválida.")
            if not hmac.compare_digest(token_hash, row[token_column]):
                raise HTTPException(status_code=401, detail="Credencial inválida.")
            connection.execute(
                "UPDATE sessions SET last_activity = ? WHERE session_id = ?",
                (now, row["session_id"]),
            )
            return str(row["session_id"])

    def rate_limit(self, session_id: str, side: str) -> None:
        now = time.time()
        with self._transaction() as connection:
            self._purge(connection, now)
            self._consume_rate(connection, "session:" + side, session_id, RATE_LIMIT_PER_MINUTE, now)

    def enqueue_event(self, session_id: str, event_id: str, payload: dict) -> None:
        import json

        with self._transaction() as connection:
            amount = connection.execute(
                "SELECT COUNT(*) AS amount FROM events WHERE session_id = ?",
                (session_id,),
            ).fetchone()["amount"]
            if amount >= QUEUE_LIMIT:
                raise HTTPException(
                    status_code=429,
                    detail="Fila de eventos cheia. AURION precisa processar os eventos pendentes.",
                )
            duplicate = connection.execute(
                "SELECT 1 FROM event_dedupe WHERE session_id = ? AND event_id = ?",
                (session_id, event_id),
            ).fetchone()
            if duplicate is not None:
                raise HTTPException(status_code=409, detail="Evento duplicado.")
            connection.execute(
                "INSERT INTO event_dedupe(session_id, event_id, created_at) VALUES (?, ?, ?)",
                (session_id, event_id, time.time()),
            )
            connection.execute(
                """
                DELETE FROM event_dedupe
                WHERE sequence IN (
                    SELECT sequence FROM event_dedupe
                    WHERE session_id = ?
                    ORDER BY sequence DESC LIMIT -1 OFFSET ?
                )
                """,
                (session_id, EVENT_DEDUPE_LIMIT),
            )
            connection.execute(
                "INSERT INTO events(session_id, event_id, payload) VALUES (?, ?, ?)",
                (session_id, event_id, json.dumps(payload, ensure_ascii=False, separators=(",", ":"))),
            )

    def get_events(self, session_id: str) -> list[dict]:
        import json

        with self.lock:
            rows = self.connection.execute(
                "SELECT payload FROM events WHERE session_id = ? ORDER BY sequence",
                (session_id,),
            ).fetchall()
            return [json.loads(row["payload"]) for row in rows]

    def enqueue_reply(self, session_id: str, event_id: str, payload: dict) -> None:
        import json

        with self._transaction() as connection:
            event = connection.execute(
                "SELECT 1 FROM event_dedupe WHERE session_id = ? AND event_id = ?",
                (session_id, event_id),
            ).fetchone()
            if event is None:
                raise HTTPException(status_code=404, detail="Evento não encontrado nesta sessão.")
            duplicate = connection.execute(
                "SELECT 1 FROM reply_dedupe WHERE session_id = ? AND event_id = ?",
                (session_id, event_id),
            ).fetchone()
            if duplicate is not None:
                raise HTTPException(status_code=409, detail="Resposta para este evento já registrada.")
            amount = connection.execute(
                "SELECT COUNT(*) AS amount FROM replies WHERE session_id = ?",
                (session_id,),
            ).fetchone()["amount"]
            if amount >= QUEUE_LIMIT:
                raise HTTPException(
                    status_code=429,
                    detail="Fila de respostas cheia. O servidor precisa entregar as respostas pendentes.",
                )
            connection.execute(
                "INSERT INTO reply_dedupe(session_id, event_id, created_at) VALUES (?, ?, ?)",
                (session_id, event_id, time.time()),
            )
            connection.execute(
                """
                DELETE FROM reply_dedupe
                WHERE sequence IN (
                    SELECT sequence FROM reply_dedupe
                    WHERE session_id = ?
                    ORDER BY sequence DESC LIMIT -1 OFFSET ?
                )
                """,
                (session_id, EVENT_DEDUPE_LIMIT),
            )
            connection.execute(
                "INSERT INTO replies(session_id, event_id, payload) VALUES (?, ?, ?)",
                (session_id, event_id, json.dumps(payload, ensure_ascii=False, separators=(",", ":"))),
            )
            connection.execute(
                "DELETE FROM events WHERE session_id = ? AND event_id = ?",
                (session_id, event_id),
            )

    def get_replies(self, session_id: str) -> list[dict]:
        import json

        with self.lock:
            rows = self.connection.execute(
                "SELECT payload FROM replies WHERE session_id = ? ORDER BY sequence",
                (session_id,),
            ).fetchall()
            return [json.loads(row["payload"]) for row in rows]

    def acknowledge_reply(self, session_id: str, event_id: str) -> bool:
        with self._transaction() as connection:
            result = connection.execute(
                "DELETE FROM replies WHERE session_id = ? AND event_id = ?",
                (session_id, event_id),
            )
            return result.rowcount > 0

    def reset(self) -> None:
        with self._transaction() as connection:
            connection.execute("DELETE FROM sessions")
            connection.execute("DELETE FROM pairings")
            connection.execute("DELETE FROM rate_limits")

    def close(self) -> None:
        with self.lock:
            self.connection.close()


class PairClaim(BaseModel):
    pairing_code: str = Field(min_length=8, max_length=8, pattern=r"^[0-9]{8}$")


class GameEvent(BaseModel):
    event_id: str = Field(min_length=8, max_length=80)
    event_type: str = Field(pattern=r"^(interaction|chat)$")
    player: str = Field(min_length=1, max_length=48)
    npc: str = Field(min_length=1, max_length=80)
    npc_id: str = Field(default="", max_length=128)
    npc_type: str = Field(default="", max_length=80)
    message: str = Field(default="", max_length=500)
    world_id: str = Field(default="default", min_length=1, max_length=80)


class AURIONReply(BaseModel):
    event_id: str = Field(min_length=8, max_length=80)
    message: str = Field(min_length=1, max_length=1200)
    npc: str = Field(min_length=1, max_length=80)


class ReplyAck(BaseModel):
    event_id: str = Field(min_length=8, max_length=80)


store = RelayStore()
app = FastAPI(title="AURION Minecraft Relay", version="0.2.0")


def _client_address(request: Request) -> str:
    # Do not trust X-Forwarded-For from arbitrary clients. Configure trusted
    # proxy handling at the hosting layer if IP-aware throttling is required.
    return request.client.host if request.client else "unknown"


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "component": "aurion-minecraft-relay",
        "storage": store.storage_mode,
    }


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
    session_id = store.authenticate(authorization, "server")
    store.rate_limit(session_id, "server")
    store.enqueue_event(
        session_id,
        body.event_id,
        body.model_dump(exclude_defaults=True),
    )
    return {"accepted": body.event_id}


@app.get("/v1/app/events")
def app_events(authorization: str | None = Header(default=None)) -> dict[str, list[dict]]:
    session_id = store.authenticate(authorization, "app")
    store.rate_limit(session_id, "app")
    return {"events": store.get_events(session_id)}


@app.post("/v1/app/replies", status_code=202)
def app_reply(body: AURIONReply, authorization: str | None = Header(default=None)) -> dict[str, str]:
    session_id = store.authenticate(authorization, "app")
    store.rate_limit(session_id, "app")
    store.enqueue_reply(session_id, body.event_id, body.model_dump())
    return {"accepted": body.event_id}


@app.get("/v1/server/replies")
def server_replies(authorization: str | None = Header(default=None)) -> dict[str, list[dict]]:
    session_id = store.authenticate(authorization, "server")
    store.rate_limit(session_id, "server")
    # Non-destructive reads let the BDS companion retry until delivery succeeds.
    return {"replies": store.get_replies(session_id)}


@app.post("/v1/server/ack")
def server_ack(body: ReplyAck, authorization: str | None = Header(default=None)) -> dict[str, str]:
    session_id = store.authenticate(authorization, "server")
    store.rate_limit(session_id, "server")
    if not store.acknowledge_reply(session_id, body.event_id):
        raise HTTPException(status_code=404, detail="Resposta não encontrada nesta sessão.")
    return {"acknowledged": body.event_id}
