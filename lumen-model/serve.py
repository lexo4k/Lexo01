"""Servidor de inferência do modelo próprio NEXORA-1.

Carrega apenas checkpoints treinados pelo projeto. Não usa API de IA externa.
A ausência de checkpoint é reportada como indisponibilidade, nunca substituída
silenciosamente por outro fornecedor.
"""
from __future__ import annotations

import os
from pathlib import Path
from threading import Lock

import torch
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from model import LumenGPT, encode, decode

APP_NAME = "NEXORA OWN MODEL"
CHECKPOINT = Path(os.getenv("NEXORA_MODEL_CHECKPOINT", "artifacts/lumen-1.pt"))
ACCESS_TOKEN = os.getenv("NEXORA_MODEL_TOKEN", "").strip()
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

app = FastAPI(title=APP_NAME, version="0.1.0")
_model = None
_model_lock = Lock()
_load_error = None


def load_model():
    global _model, _load_error
    with _model_lock:
        if _model is not None:
            return _model
        if not CHECKPOINT.is_file():
            _load_error = "checkpoint_missing"
            return None
        try:
            checkpoint = torch.load(CHECKPOINT, map_location=DEVICE, weights_only=True)
            model = LumenGPT(**checkpoint["config"]).to(DEVICE)
            model.load_state_dict(checkpoint["state_dict"])
            model.eval()
            _model = model
            _load_error = None
            return _model
        except Exception as exc:
            _load_error = type(exc).__name__
            return None


class GenerateIn(BaseModel):
    prompt: str = Field(min_length=1, max_length=6000)
    max_new_tokens: int = Field(default=160, ge=1, le=512)
    temperature: float = Field(default=0.8, ge=0.1, le=1.5)
    top_k: int = Field(default=40, ge=1, le=100)


@app.get("/health")
def health():
    model = load_model()
    checkpoint_step = None
    if model is not None:
        try:
            data = torch.load(CHECKPOINT, map_location="cpu", weights_only=True)
            checkpoint_step = int(data.get("step", 0))
        except Exception:
            pass
    return {
        "service": APP_NAME,
        "status": "ready" if model is not None else "not_ready",
        "engine": "nexora-transformer-byte-v1",
        "own_weights": True,
        "checkpoint_present": CHECKPOINT.is_file(),
        "checkpoint_step": checkpoint_step,
        "device": DEVICE,
        "error": _load_error,
    }


@app.post("/generate")
def generate(item: GenerateIn, x_model_token: str | None = Header(default=None)):
    if not ACCESS_TOKEN:
        raise HTTPException(503, "Configure NEXORA_MODEL_TOKEN no servidor.")
    if x_model_token != ACCESS_TOKEN:
        raise HTTPException(401, "Token do modelo inválido.")
    model = load_model()
    if model is None:
        raise HTTPException(503, "Modelo próprio indisponível: checkpoint treinado não encontrado ou inválido.")
    tokens = encode(item.prompt)
    context = model.context
    tokens = tokens[-context:]
    input_ids = torch.tensor([tokens], dtype=torch.long, device=DEVICE)
    with torch.inference_mode():
        output = model.generate(
            input_ids,
            max_new_tokens=item.max_new_tokens,
            temperature=item.temperature,
            top_k=item.top_k,
        )
    generated = output[0, len(tokens):].tolist()
    return {
        "text": decode(generated),
        "engine": "nexora-transformer-byte-v1",
        "checkpoint_step": int(torch.load(CHECKPOINT, map_location="cpu", weights_only=True).get("step", 0)),
        "warning": "Modelo experimental de previsão de texto; não equivale a um assistente conversacional validado.",
    }
