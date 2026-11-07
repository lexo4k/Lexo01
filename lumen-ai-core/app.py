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
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

from cognition import think as cognitive_cycle

ROOT = Path(__file__).parent
DB_PATH = Path(os.getenv("LUMEN_DB_PATH", str(ROOT / "data" / "lumen.db")))
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="LÚMEN AI CORE", version="0.2.0", description="Núcleo pessoal de IA com memória persistente.")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
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

def _pg_row_factory(cursor, values):
    class Row(dict):
        def __getitem__(self, key):
            if isinstance(key, int):
                return list(self.values())[key]
            return super().__getitem__(key)
    return Row((column.name, value) for column, value in zip(cursor.description, values))

class _PgCursor:
    def __init__(self, cursor, lastrowid=None):
        self._cursor = cursor
        self.lastrowid = lastrowid
        self.rowcount = cursor.rowcount
    def fetchone(self):
        return self._cursor.fetchone()
    def fetchall(self):
        return self._cursor.fetchall()

class _PgConnection:
    def __init__(self, connection):
        self._connection = connection
    def execute(self, sql, params=()):
        statement = sql.replace("?", "%s")
        is_insert = statement.lstrip().upper().startswith("INSERT")
        if is_insert and " RETURNING " not in statement.upper():
            statement = statement.rstrip().rstrip(";") + " RETURNING id"
        cursor = self._connection.cursor()
        cursor.execute(statement, params)
        lastrowid = None
        if is_insert:
            row = cursor.fetchone()
            lastrowid = row["id"] if row else None
        return _PgCursor(cursor, lastrowid)
    def executescript(self, script):
        for statement in script.split(";"):
            if statement.strip():
                statement = statement.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "BIGSERIAL PRIMARY KEY")
                self._connection.execute(statement)
    def commit(self):
        self._connection.commit()
    def rollback(self):
        self._connection.rollback()
    def close(self):
        self._connection.close()

@contextmanager
def db():
    if DATABASE_URL:
        import psycopg
        con = _PgConnection(psycopg.connect(DATABASE_URL, row_factory=_pg_row_factory))
    else:
        con = sqlite3.connect(DB_PATH)
        con.row_factory = sqlite3.Row
    try:
        con.executescript(SCHEMA)
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
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

class ThinkIn(BaseModel):
    goal: str = Field(min_length=1, max_length=8000)

class ResearchIn(BaseModel):
    query: str = Field(min_length=2, max_length=2000)

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

@app.get("/manifest.webmanifest")
def web_manifest():
    return FileResponse(ROOT / "manifest.webmanifest", media_type="application/manifest+json")

@app.get("/sw.js")
def service_worker():
    return FileResponse(ROOT / "sw.js", media_type="application/javascript", headers={"Service-Worker-Allowed": "/"})

@app.get("/icon.svg")
def app_icon():
    return FileResponse(ROOT / "icon.svg", media_type="image/svg+xml")

@app.get("/api/capabilities", dependencies=[Depends(require_access)])
def capabilities():
    ready = bool(os.getenv("OPENAI_API_KEY", "").strip())
    return {"chat": {"implemented": True, "configured": ready},
            "web_research": {"implemented": True, "configured": ready},
            "memory": {"implemented": True, "configured": True},
            "voice_input": {"implemented": True, "configured": True, "depends_on": "browser"},
            "voice_output": {"implemented": True, "configured": True, "depends_on": "browser"},
            "image_input": {"implemented": True, "configured": ready},
            "planning": {"implemented": True, "configured": ready},
            "ads": {"implemented": False, "configured": False},
            "persistent_storage": {"implemented": True, "configured": bool(DATABASE_URL), "durability": "managed_postgresql" if DATABASE_URL else "depends_on_server_disk"}}

@app.get("/api/health")
def health():
    return {"app": "LÚMEN AI CORE", "status": "online", "version": app.version,
            "model_connected": False,
            "model_key_configured": bool(os.getenv("OPENAI_API_KEY", "").strip()),
            "access_configured": bool(os.getenv("LUMEN_ACCESS_TOKEN")),
            "web_research_key_configured": bool(os.getenv("OPENAI_API_KEY")),
            "primary_experience": "chat", "storage_backend": "postgresql" if DATABASE_URL else "sqlite"}

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

@app.post("/api/research", dependencies=[Depends(require_access)])
async def research_web(item: ResearchIn):
    """Pesquisa na web usando a ferramenta web_search do provedor e devolve fontes."""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(503, "Pesquisa web indisponível: conecte OPENAI_API_KEY ao servidor.")
    base = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("LUMEN_RESEARCH_MODEL", "gpt-4.1")
    payload = {
        "model": model,
        "tools": [{"type": "web_search"}],
        "tool_choice": "auto",
        "include": ["web_search_call.action.sources"],
        "input": (
            "Pesquise na web a pergunta a seguir. Priorize fontes primárias e confiáveis, "
            "compare informações quando necessário, informe datas relevantes, diferencie "
            "fatos de inferências e não invente dados. Responda em português claro e cite "
            "as fontes consultadas. Pergunta: " + item.query
        )
    }
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{base}/responses",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=payload
            )
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(502, f"Pesquisa web falhou no provedor (HTTP {exc.response.status_code}). Verifique se o modelo e a API oferecem web_search.") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(502, "Não foi possível acessar o serviço de pesquisa web.") from exc

    answer_parts = []
    sources = []
    for output in data.get("output", []):
        if output.get("type") == "message":
            for part in output.get("content", []):
                if part.get("type") in ("output_text", "text") and part.get("text"):
                    answer_parts.append(part["text"])
                for annotation in part.get("annotations", []):
                    if annotation.get("type") == "url_citation":
                        sources.append({
                            "title": annotation.get("title") or annotation.get("url", ""),
                            "url": annotation.get("url", "")
                        })
        action = output.get("action", {})
        for source in action.get("sources", []):
            sources.append({"title": source.get("title") or source.get("url", ""),
                            "url": source.get("url", "")})
    answer = data.get("output_text") or "\n".join(answer_parts)
    unique = []
    seen = set()
    for source in sources:
        url = source.get("url", "")
        if url.startswith("https://") and url not in seen:
            seen.add(url)
            unique.append(source)
    if not answer:
        raise HTTPException(502, "A pesquisa foi concluída sem texto de resposta.")
    with db() as con:
        stamp = now()
        source_text = "\n".join(
            f'{source.get("title") or source["url"]}: {source["url"]}'
            for source in unique[:20]
        )
        stored_answer = answer + (("\n\nFontes consultadas:\n" + source_text) if source_text else "")
        con.execute("INSERT INTO conversation_messages(role,content,created_at) VALUES('user',?,?)",
                    (item.query, stamp))
        con.execute("INSERT INTO conversation_messages(role,content,created_at) VALUES('assistant',?,?)",
                    (stored_answer, stamp))
        con.execute("INSERT INTO journal(event,detail,created_at) VALUES(?,?,?)",
                    ("Pesquisa web concluída", item.query[:180], stamp))
    return {"query": item.query, "answer": answer, "sources": unique[:20],
            "model": model, "web_search_used": True}

@app.post("/api/think", dependencies=[Depends(require_access)])
async def think_endpoint(item: ThinkIn):
    """Planeja e avalia um objetivo sem executar ações externas."""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(503, "O motor cognitivo está implementado, mas depende de um provedor de IA conectado.")
    base = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    with db() as con:
        memories = [r["content"] for r in con.execute(
            "SELECT content FROM memories ORDER BY id DESC LIMIT 40"
        )]
        knowledge = [f'{r["title"]}: {r["content"]}' for r in con.execute(
            "SELECT title,content FROM knowledge ORDER BY id DESC LIMIT 30"
        )]
        history = [dict(r) for r in con.execute(
            "SELECT role,content FROM conversation_messages ORDER BY id DESC LIMIT 12"
        )][::-1]
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            result = await cognitive_cycle(
                client=client, base=base, key=api_key, model=model, goal=item.goal,
                memories=memories, knowledge=knowledge, recent_history=history
            )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(502, f"Provedor de IA respondeu com erro HTTP {exc.response.status_code}.") from exc
    except (httpx.HTTPError, KeyError, IndexError, ValueError, TypeError) as exc:
        raise HTTPException(502, "O ciclo cognitivo não conseguiu concluir uma avaliação válida.") from exc
    with db() as con:
        con.execute("INSERT INTO journal(event,detail,created_at) VALUES(?,?,?)",
                    ("Ciclo cognitivo concluído", item.goal[:180], now()))
    return result

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
