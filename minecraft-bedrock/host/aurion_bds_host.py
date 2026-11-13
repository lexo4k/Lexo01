#!/usr/bin/env python3
"""Run official Bedrock Dedicated Server with the AURION relay companion.

The behavior pack writes structured interaction events to the BDS console.
This companion forwards them over HTTPS and injects generated replies with
/tellraw. It never generates dialogue and never stores credentials in the pack.
"""
from __future__ import annotations

import argparse
import json
import os
import queue
import re
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

EVENT_MARKER = "AURION_EVENT "
EVENT_ID_RE = re.compile(r"^aurion-[a-z0-9-]{8,64}$")
MAX_EVENT_LINE = 8192


class RelayError(RuntimeError):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


def normalize_relay_url(value: str) -> str:
    parsed = urllib.parse.urlsplit(value.strip())
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError("O relay precisa ser um endereço HTTPS válido.")
    if parsed.query or parsed.fragment:
        raise ValueError("O endereço do relay não pode conter query ou fragmento.")
    return value.strip().rstrip("/")


def _bounded_text(value: Any, field: str, limit: int, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ValueError(f"Campo {field} inválido.")
    value = value.strip()
    if (not value and not allow_empty) or len(value) > limit:
        raise ValueError(f"Campo {field} fora do limite permitido.")
    if any(ord(char) < 32 and char not in "\t" for char in value):
        raise ValueError(f"Campo {field} contém caracteres de controle.")
    return value


def validate_game_event(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        raise ValueError("Evento AURION inválido.")
    event_id = _bounded_text(value.get("event_id"), "event_id", 80)
    if not EVENT_ID_RE.fullmatch(event_id):
        raise ValueError("Identificador de evento inválido.")
    event_type = _bounded_text(value.get("event_type"), "event_type", 20)
    if event_type != "interaction":
        raise ValueError("Tipo de evento ainda não suportado.")
    return {
        "event_id": event_id,
        "event_type": event_type,
        "player": _bounded_text(value.get("player"), "player", 48),
        "npc": _bounded_text(value.get("npc"), "npc", 80),
        "npc_id": _bounded_text(value.get("npc_id", ""), "npc_id", 128, allow_empty=True),
        "npc_type": _bounded_text(value.get("npc_type", ""), "npc_type", 80, allow_empty=True),
        "message": _bounded_text(value.get("message", ""), "message", 500, allow_empty=True),
        "world_id": _bounded_text(value.get("world_id", "aurion-bds-world"), "world_id", 80),
    }


def extract_event(line: str) -> dict[str, str] | None:
    marker_at = line.find(EVENT_MARKER)
    if marker_at < 0:
        return None
    raw = line[marker_at + len(EVENT_MARKER):].strip()
    if not raw or len(raw) > MAX_EVENT_LINE:
        raise ValueError("Linha de evento vazia ou grande demais.")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("JSON do evento AURION malformado.") from exc
    return validate_game_event(payload)


def build_tellraw_command(player: str, npc: str, message: str) -> str:
    player = _bounded_text(player, "player", 48)
    npc = _bounded_text(npc, "npc", 80)
    message = _bounded_text(message, "message", 1200)
    selector = "@a[name=" + json.dumps(player, ensure_ascii=False) + "]"
    payload = {"rawtext": [{"text": "§b" + npc + "§r §7»§r " + message}]}
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return "tellraw " + selector + " " + encoded


def _atomic_json_write(path: Path, value: dict[str, Any]) -> None:
    path = path.expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        if hasattr(os, "fchmod"):
            os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, separators=(",", ":"))
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def save_credentials(path: Path, relay_url: str, session_id: str, server_token: str) -> None:
    if len(server_token) < 32 or not session_id:
        raise ValueError("O relay devolveu credenciais inválidas.")
    _atomic_json_write(path, {
        "relay_url": normalize_relay_url(relay_url),
        "session_id": session_id,
        "server_token": server_token,
    })


def load_credentials(path: Path, relay_url: str) -> dict[str, str]:
    data = json.loads(path.expanduser().read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Arquivo de credenciais inválido.")
    stored_url = normalize_relay_url(str(data.get("relay_url", "")))
    if stored_url != normalize_relay_url(relay_url):
        raise ValueError("O arquivo de credenciais pertence a outro relay.")
    token = str(data.get("server_token", ""))
    session_id = str(data.get("session_id", ""))
    if len(token) < 32 or not session_id:
        raise ValueError("Credenciais locais incompletas. Faça um novo pareamento.")
    return {"relay_url": stored_url, "session_id": session_id, "server_token": token}


def load_pending(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(value, dict):
        return {}
    return {
        key: record for key, record in value.items()
        if isinstance(key, str) and isinstance(record, dict)
        and isinstance(record.get("player"), str)
        and isinstance(record.get("event"), dict)
    }


def save_pending(path: Path, pending: dict[str, dict[str, Any]]) -> None:
    _atomic_json_write(path, pending)


def request_json(
    relay_url: str,
    path: str,
    method: str = "GET",
    token: str | None = None,
    payload: dict[str, Any] | None = None,
    timeout: float = 10.0,
) -> dict[str, Any]:
    root = normalize_relay_url(relay_url)
    headers = {"Accept": "application/json"}
    body = None
    if token:
        headers["Authorization"] = "Bearer " + token
    if payload is not None:
        headers["Content-Type"] = "application/json; charset=utf-8"
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(root + path, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            message = json.loads(raw).get("detail", "")
        except (json.JSONDecodeError, AttributeError):
            message = ""
        raise RelayError(exc.code, str(message or f"Relay respondeu HTTP {exc.code}.")) from exc
    except urllib.error.URLError as exc:
        raise RelayError(0, "Não foi possível alcançar o relay: " + str(exc.reason)) from exc


def claim_pairing(relay_url: str, code: str) -> dict[str, str]:
    if not re.fullmatch(r"[0-9]{8}", code.strip()):
        raise ValueError("O código de pareamento precisa ter oito dígitos.")
    result = request_json(
        relay_url, "/v1/pair/claim", method="POST",
        payload={"pairing_code": code.strip()},
    )
    return {
        "session_id": str(result.get("session_id", "")),
        "server_token": str(result.get("server_token", "")),
    }


def post_pending_events(relay_url: str, token: str, pending: dict[str, dict[str, Any]], pending_path: Path) -> None:
    changed = False
    for event_id, record in list(pending.items()):
        if record.get("submitted") is True:
            continue
        try:
            request_json(relay_url, "/v1/server/events", method="POST", token=token, payload=record["event"])
        except RelayError as exc:
            if exc.status != 409:
                if exc.status == 401:
                    raise
                print("AURION relay: evento aguardando reenvio: " + str(exc), file=sys.stderr)
                continue
        record["submitted"] = True
        changed = True
        print("AURION relay: interação recebida para processamento local.")
    if changed:
        save_pending(pending_path, pending)


def deliver_replies(
    relay_url: str,
    token: str,
    process: subprocess.Popen[str],
    pending: dict[str, dict[str, Any]],
    pending_path: Path,
) -> int:
    result = request_json(relay_url, "/v1/server/replies", token=token)
    replies = result.get("replies", [])
    if not isinstance(replies, list):
        raise ValueError("Fila de respostas do relay inválida.")
    delivered = 0
    for reply in replies:
        if not isinstance(reply, dict):
            continue
        event_id = str(reply.get("event_id", ""))
        record = pending.get(event_id)
        if record is None:
            print("AURION relay: resposta sem interação local correspondente; mantida na fila.", file=sys.stderr)
            continue
        command = build_tellraw_command(
            str(record["player"]),
            str(reply.get("npc", record.get("npc", "NPC"))),
            str(reply.get("message", "")),
        )
        if process.poll() is not None or process.stdin is None:
            raise RuntimeError("O servidor Bedrock encerrou antes da entrega.")
        process.stdin.write(command + "\n")
        process.stdin.flush()
        request_json(
            relay_url, "/v1/server/ack", method="POST", token=token,
            payload={"event_id": event_id},
        )
        pending.pop(event_id, None)
        save_pending(pending_path, pending)
        delivered += 1
        print("AURION relay: resposta enviada ao console do servidor para " + str(record["player"]) + ".")
    return delivered


def _server_binary(server_dir: Path, explicit: str | None) -> Path:
    if explicit:
        candidate = Path(explicit).expanduser()
        if not candidate.is_absolute():
            candidate = server_dir / candidate
    else:
        candidate = server_dir / ("bedrock_server.exe" if os.name == "nt" else "bedrock_server")
    candidate = candidate.resolve()
    if not candidate.is_file():
        raise FileNotFoundError("Executável oficial BDS não encontrado: " + str(candidate))
    return candidate


def run_bridge(args: argparse.Namespace) -> int:
    relay_url = normalize_relay_url(args.relay_url)
    credentials_path = Path(args.credentials).expanduser()
    if credentials_path.exists() and not args.pairing_code:
        credentials = load_credentials(credentials_path, relay_url)
        print("AURION: credenciais do servidor recuperadas do armazenamento local.")
    else:
        code = args.pairing_code or input("Código de pareamento exibido no AURION (8 dígitos): ").strip()
        credentials = claim_pairing(relay_url, code)
        save_credentials(
            credentials_path, relay_url,
            credentials["session_id"], credentials["server_token"],
        )
        print("AURION: pareamento concluído. Token salvo em arquivo privado; não será exibido.")
    token = credentials["server_token"]
    pending_path = credentials_path.with_name("pending-events.json")
    pending = load_pending(pending_path)
    server_dir = Path(args.server_dir).expanduser().resolve()
    binary = _server_binary(server_dir, args.server_executable)
    process = subprocess.Popen(
        [str(binary)],
        cwd=str(server_dir),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    lines: queue.Queue[str] = queue.Queue()

    def read_output() -> None:
        assert process.stdout is not None
        for line in process.stdout:
            lines.put(line)

    threading.Thread(target=read_output, daemon=True).start()
    print("AURION: servidor Bedrock iniciado. Aguardando interações com NPCs identificados.")
    poll_interval = max(4.0, min(float(args.poll_interval), 15.0))
    next_poll = 0.0
    try:
        while process.poll() is None:
            try:
                while True:
                    line = lines.get_nowait()
                    sys.stdout.write(line)
                    sys.stdout.flush()
                    try:
                        event = extract_event(line)
                    except ValueError as exc:
                        print("AURION: evento ignorado: " + str(exc), file=sys.stderr)
                        continue
                    if event is not None and event["event_id"] not in pending:
                        pending[event["event_id"]] = {
                            "player": event["player"],
                            "npc": event["npc"],
                            "event": event,
                            "submitted": False,
                        }
                        save_pending(pending_path, pending)
            except queue.Empty:
                pass
            now = time.monotonic()
            if now >= next_poll:
                try:
                    post_pending_events(relay_url, token, pending, pending_path)
                    deliver_replies(relay_url, token, process, pending, pending_path)
                except RelayError as exc:
                    if exc.status == 401:
                        raise RuntimeError("Sessão do relay expirada ou reiniciada. Gere um novo código no AURION e execute novamente com --pairing-code.") from exc
                    print("AURION relay: " + str(exc), file=sys.stderr)
                next_poll = now + poll_interval
            time.sleep(0.1)
        return int(process.returncode or 0)
    except KeyboardInterrupt:
        print("\nAURION: encerrando o servidor…")
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
        return 130
    finally:
        if process.poll() is None:
            process.terminate()
        if process.stdin:
            process.stdin.close()
        if process.stdout:
            process.stdout.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Conecta um Bedrock Dedicated Server ao AURION local.")
    parser.add_argument("--server-dir", required=True, help="Pasta do Bedrock Dedicated Server oficial.")
    parser.add_argument("--relay-url", required=True, help="URL HTTPS do relay AURION.")
    parser.add_argument("--pairing-code", help="Código de oito dígitos mostrado pelo aplicativo AURION.")
    parser.add_argument("--server-executable", help="Executável BDS; por padrão bedrock_server(.exe).")
    parser.add_argument(
        "--credentials",
        default=str(Path.home() / ".aurion-minecraft" / "credentials.json"),
        help="Arquivo privado para credenciais do servidor.",
    )
    parser.add_argument("--poll-interval", type=float, default=5.0, help="Intervalo de consulta do relay em segundos.")
    args = parser.parse_args()
    try:
        return run_bridge(args)
    except (OSError, ValueError, RelayError, RuntimeError) as exc:
        print("AURION BDS: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
