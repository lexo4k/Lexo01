from __future__ import annotations

import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, field_validator

ROOT = Path(__file__).parent
DB_PATH = Path(os.getenv("LUMEN_DB_PATH", str(ROOT / "data" / "lumen.db")))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="LÚMEN AI CORE", version="0.1.0", description="Núcleo pessoal de IA com memória persistente.")
SCHEMA = """
CREATE TABLE IF NOT EXISTS memories (
 id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT NOT NULL,
 category TEXT NOT NULL DEFAULT 'geral', created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS knowledge (
 id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,
 content TEXT NOT NULL, source TEXT NOT NULL DEFAULT '',
 created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tasks (
 id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,
 details TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'pendente',
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS journal (
 id INTEGER PRIMARY KEY AUTOINCREMENT, event TEXT NOT NULL,
 detail TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS conversation_messages (
 id INTEGER PRIMARY KEY AUTOINCREMENT, role TEXT NOT NULL CHECK(role IN ('user','assistant')),
 content TEXT NOT NULL, created_at TEXT NOT NULL
);
"""

@contextmanager
def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        con.executescript(SCHEMA)
        yield con
        con.commit()
    finally:
        con.close()

def now() -> str:
    return datetime.now(timezone.utc).isoformat()

def require_access(authorization: str | None = Header(default=None)) -> None:
    expected = os.getenv("LUMEN_ACCESS_TOKEN", "").strip()
    if not expected:
        raise HTTPException(503, "Configure LUMEN_ACCESS_TOKEN no ambiente do servidor antes de usar a API.")
    supplied = (authorization or "").removeprefix("Bearer ").strip()
    if not secrets.compare_digest(supplied, expected):
        raise HTTPException(401, "Token de acesso inválido.")

class MemoryIn(BaseModel):
    content: str = Field(min_length=1, max_length=8000)
    category: str = Field(default="geral", max_length=80)

class KnowledgeIn(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    content: str = Field(min_length=1, max_length=12000)
    source: str = Field(default="", max_length=1000)

class TaskIn(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    details: str = Field(default="", max_length=4000)

class TaskUpdate(BaseModel):
    status: str = Field(pattern="^(pendente|em andamento|concluída)$")

class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    image_data_url: str | None = Field(default=None, max_length=7_000_000)

    @field_validator("image_data_url")
    @classmethod
    def validate_image(cls, value):
        if value is not None and not value.startswith(("data:image/jpeg;base64,", "data:image/png;base64,", "data:image/webp;base64,")):
            raise ValueError("Envie uma imagem JPEG, PNG ou WebP.")
        return value

@app.get("/", response_class=HTMLResponse)
def home():
    return (ROOT / "index.html").read_text(encoding="utf-8")

@app.get("/api/health")
def health():
    return {"app": "LÚMEN AI CORE", "status": "online", "version": app.version,
            "model_connected": bool(os.getenv("OPENAI_API_KEY")),
            "access_configured": bool(os.getenv("LUMEN_ACCESS_TOKEN"))}

@app.get("/api/overview", dependencies=[Depends(require_access)])
def overview():
    with db() as con:
        return {
            "memories": con.execute("SELECT COUNT(*) FROM memories").fetchone()[0],
            "knowledge": con.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0],
            "open_tasks": con.execute("SELECT COUNT(*) FROM tasks WHERE status != 'concluída'").fetchone()[0],
            "recent_journal": [dict(r) for r in con.execute("SELECT * FROM journal ORDER BY id DESC LIMIT 8")]
        }

@app.get("/api/memories", dependencies=[Depends(require_access)])
def list_memories():
    with db() as con:
        return [dict(r) for r in con.execute("SELECT * FROM memories ORDER BY id DESC LIMIT 300")]

@app.post("/api/memories", dependencies=[Depends(require_access)])
def add_memory(item: MemoryIn):
    with db() as con:
        cur = con.execute("INSERT INTO memories(content,category,created_at) VALUES(?,?,?)",
                          (item.content, item.category, now()))
        con.execute("INSERT INTO journal(event,detail,created_at) VALUES(?,?,?)",
                    ("Memória registrada", item.category, now()))
        return {"id": cur.lastrowid, "saved": True}

@app.delete("/api/memories/{memory_id}", dependencies=[Depends(require_access)])
def delete_memory(memory_id: int):
    with db() as con:
        cur = con.execute("DELETE FROM memories WHERE id=?", (memory_id,))
        if not cur.rowcount:
            raise HTTPException(404, "Memória não encontrada.")
        return {"deleted": True}

@app.get("/api/knowledge", dependencies=[Depends(require_access)])
def list_knowledge():
    with db() as con:
        return [dict(r) for r in con.execute("SELECT * FROM knowledge ORDER BY id DESC LIMIT 300")]

@app.post("/api/knowledge", dependencies=[Depends(require_access)])
def add_knowledge(item: KnowledgeIn):
    with db() as con:
        cur = con.execute("INSERT INTO knowledge(title,content,source,created_at) VALUES(?,?,?,?)",
                          (item.title, item.content, item.source, now()))
        con.execute("INSERT INTO journal(event,detail,created_at) VALUES(?,?,?)",
                    ("Conhecimento arquivado", item.title, now()))
        return {"id": cur.lastrowid, "saved": True}

@app.get("/api/tasks", dependencies=[Depends(require_access)])
def list_tasks():
    with db() as con:
        return [dict(r) for r in con.execute("SELECT * FROM tasks ORDER BY id DESC LIMIT 300")]

@app.post("/api/tasks", dependencies=[Depends(require_access)])
def add_task(item: TaskIn):
    stamp = now()
    with db() as con:
        cur = con.execute("INSERT INTO tasks(title,details,status,created_at,updated_at) VALUES(?,?, 'pendente',?,?)",
                          (item.title, item.details, stamp, stamp))
        con.execute("INSERT INTO journal(event,detail,created_at) VALUES(?,?,?)",
                    ("Tarefa criada", item.title, stamp))
        return {"id": cur.lastrowid, "saved": True}

@app.patch("/api/tasks/{task_id}", dependencies=[Depends(require_access)])
def update_task(task_id: int, item: TaskUpdate):
    with db() as con:
        cur = con.execute("UPDATE tasks SET status=?,updated_at=? WHERE id=?",
                          (item.status, now(), task_id))
        if not cur.rowcount:
            raise HTTPException(404, "Tarefa não encontrada.")
        con.execute("INSERT INTO journal(event,detail,created_at) VALUES(?,?,?)",
                    ("Tarefa atualizada", f"{task_id}: {item.status}", now()))
        return {"updated": True}

@app.delete("/api/tasks/{task_id}", dependencies=[Depends(require_access)])
def delete_task(task_id: int):
    with db() as con:
        cur = con.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        if not cur.rowcount:
            raise HTTPException(404, "Tarefa não encontrada.")
        return {"deleted": True}

@app.get("/api/journal", dependencies=[Depends(require_access)])
def journal():
    with db() as con:
        return [dict(r) for r in con.execute("SELECT * FROM journal ORDER BY id DESC LIMIT 100")]

@app.get("/api/conversations", dependencies=[Depends(require_access)])
def conversations(limit: int = 100):
    limit = max(1, min(limit, 300))
    with db() as con:
        rows = con.execute(
            "SELECT id,role,content,created_at FROM conversation_messages ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(row) for row in reversed(rows)]

@app.post("/api/chat", dependencies=[Depends(require_access)])
async def chat(item: ChatIn):
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(503, "O núcleo está ativo, mas o modelo de IA ainda não foi conectado. Configure OPENAI_API_KEY no servidor.")
    base = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    with db() as con:
        memories = [r["content"] for r in con.execute("SELECT content FROM memories ORDER BY id DESC LIMIT 20")]
        facts = [f'{r["title"]}: {r["content"]}' for r in con.execute("SELECT title,content FROM knowledge ORDER BY id DESC LIMIT 10")]
        history = [dict(r) for r in con.execute(
            "SELECT role,content FROM conversation_messages ORDER BY id DESC LIMIT 20"
        )][::-1]
    context = "\n".join([*(f"- {m}" for m in memories), *(f"- {f}" for f in facts)])
    system = ("Você é LÚMEN, um assistente de IA claro, útil e honesto. Não alegue consciência, "
              "sentimentos reais, execução em segundo plano ou ações não realizadas. Diferencie fatos, "
              "inferências e incertezas. Use o contexto salvo apenas quando relevante.\n"
              f"MEMÓRIA E CONHECIMENTO DISPONÍVEIS:\n{context or '(ainda vazios)'}")
    messages = [{"role": "system", "content": system}]
    messages.extend(history)
    user_content: Any = item.message
    if item.image_data_url:
        if not item.image_data_url.startswith(("data:image/jpeg;base64,", "data:image/png;base64,", "data:image/webp;base64,")):
            raise HTTPException(400, "Formato de imagem não aceito. Use JPEG, PNG ou WebP.")
        user_content = [
            {"type": "text", "text": item.message or "Descreva esta imagem."},
            {"type": "image_url", "image_url": {"url": item.image_data_url, "detail": "auto"}}
        ]
    messages.append({"role": "user", "content": user_content})
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(f"{base}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"model": model, "messages": messages})
            response.raise_for_status()
            answer = response.json()["choices"][0]["message"]["content"]
    except httpx.HTTPStatusError as exc:
        raise HTTPException(502, f"Provedor de IA respondeu com erro HTTP {exc.response.status_code}.") from exc
    except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
        raise HTTPException(502, "Não foi possível obter uma resposta válida do provedor de IA.") from exc
    with db() as con:
        stamp = now()
        con.execute("INSERT INTO conversation_messages(role,content,created_at) VALUES('user',?,?)",
                    (item.message, stamp))
        con.execute("INSERT INTO conversation_messages(role,content,created_at) VALUES('assistant',?,?)",
                    (answer, stamp))
        con.execute("INSERT INTO journal(event,detail,created_at) VALUES(?,?,?)",
                    ("Conversa com o modelo", item.message[:180], stamp))
    return {"answer": answer, "model": model}

@app.on_event("startup")
def startup():
    with db():
        pass
