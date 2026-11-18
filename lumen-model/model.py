"""LÚMEN-1: arquitetura experimental decoder-only treinável do zero.
Não usa pesos de terceiros. Pesos são inicializados aleatoriamente e aprendidos
somente com o corpus fornecido pelo operador.
"""
from __future__ import annotations
import math
import torch
from torch import nn
from torch.nn import functional as F

class CausalSelfAttention(nn.Module):
    def __init__(self, width: int, heads: int, dropout: float):
        super().__init__()
        if width % heads:
            raise ValueError("width precisa ser divisível por heads")
        self.heads = heads
        self.qkv = nn.Linear(width, 3 * width)
        self.proj = nn.Linear(width, width)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x):
        b, t, c = x.shape
        q, k, v = self.qkv(x).chunk(3, dim=-1)
        shape = (b, t, self.heads, c // self.heads)
        q, k, v = [z.view(shape).transpose(1, 2) for z in (q, k, v)]
        y = F.scaled_dot_product_attention(q, k, v, is_causal=True,
                                           dropout_p=self.dropout.p if self.training else 0.0)
        y = y.transpose(1, 2).contiguous().view(b, t, c)
        return self.dropout(self.proj(y))

class Block(nn.Module):
    def __init__(self, width, heads, dropout):
        super().__init__()
        self.norm1 = nn.LayerNorm(width)
        self.attn = CausalSelfAttention(width, heads, dropout)
        self.norm2 = nn.LayerNorm(width)
        self.mlp = nn.Sequential(nn.Linear(width, 4 * width), nn.GELU(),
                                 nn.Linear(4 * width, width), nn.Dropout(dropout))
    def forward(self, x):
        x = x + self.attn(self.norm1(x))
        return x + self.mlp(self.norm2(x))

class LumenGPT(nn.Module):
    """Transformer causal byte-level. Vocab UTF-8 byte = 256 + EOS."""
    def __init__(self, width=256, layers=6, heads=8, context=512, dropout=0.1):
        super().__init__()
        self.context = context
        self.token = nn.Embedding(257, width)
        self.position = nn.Embedding(context, width)
        self.blocks = nn.Sequential(*[Block(width, heads, dropout) for _ in range(layers)])
        self.norm = nn.LayerNorm(width)
        self.lm_head = nn.Linear(width, 257, bias=False)
        self.lm_head.weight = self.token.weight
        self.apply(self._init)
    @staticmethod
    def _init(module):
        if isinstance(module, nn.Linear):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)
            if module.bias is not None: nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)
    def forward(self, idx, targets=None):
        b, t = idx.shape
        if t > self.context: raise ValueError("Sequência excede context")
        pos = torch.arange(t, device=idx.device)
        x = self.token(idx) + self.position(pos)[None, :, :]
        logits = self.lm_head(self.norm(self.blocks(x)))
        loss = F.cross_entropy(logits.reshape(-1, 257), targets.reshape(-1)) if targets is not None else None
        return logits, loss
    @torch.no_grad()
    def generate(self, idx, max_new_tokens=120, temperature=0.8, top_k=40):
        self.eval()
        for _ in range(max_new_tokens):
            logits, _ = self(idx[:, -self.context:])
            logits = logits[:, -1, :] / max(temperature, 1e-5)
            if top_k:
                values, _ = torch.topk(logits, min(top_k, logits.size(-1)))
                logits[logits < values[:, [-1]]] = -float("inf")
            probs = F.softmax(logits, dim=-1)
            nxt = torch.multinomial(probs, 1)
            idx = torch.cat((idx, nxt), dim=1)
            # EOS encerra a geração quando toda a amostra terminou.
            if torch.all(nxt.squeeze(-1) == 256):
                break
        return idx

def encode(text: str) -> list[int]:
    return list(text.encode("utf-8")) + [256]

def decode(tokens) -> str:
    raw = bytes(int(x) for x in tokens if int(x) < 256)
    return raw.decode("utf-8", errors="replace")
