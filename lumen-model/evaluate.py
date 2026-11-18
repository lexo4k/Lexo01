"""Avaliação determinística em texto separado do corpus de treinamento."""
import argparse
import json
import math
from pathlib import Path

import torch
from model import LumenGPT, encode


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("checkpoint", nargs="?", default="artifacts/lumen-1.pt")
    parser.add_argument("--data", default="evaluation/heldout-pt-br.txt")
    args = parser.parse_args()

    checkpoint_path = Path(args.checkpoint)
    data_path = Path(args.data)
    if not checkpoint_path.is_file():
        raise SystemExit(f"Checkpoint não encontrado: {checkpoint_path}")
    if not data_path.is_file():
        raise SystemExit(f"Arquivo de avaliação separado não encontrado: {data_path}")

    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    config = checkpoint["config"]
    model = LumenGPT(**config)
    model.load_state_dict(checkpoint["state_dict"])
    model.eval()

    tokens = torch.tensor(encode(data_path.read_text(encoding="utf-8")), dtype=torch.long)
    context = int(config["context"])
    if len(tokens) < 2:
        raise SystemExit("Texto de avaliação vazio ou curto demais.")

    # Cada alvo é avaliado uma vez, sempre com contexto causal limitado.
    total_loss = 0.0
    total_tokens = 0
    with torch.no_grad():
        for start in range(0, len(tokens) - 1, context):
            x = tokens[start:start + context]
            y = tokens[start + 1:start + context + 1]
            if len(x) < 1 or len(y) != len(x):
                continue
            x = x.unsqueeze(0)
            y = y.unsqueeze(0)
            if x.shape[1] == 0:
                continue
            _, loss = model(x, y)
            count = y.numel()
            total_loss += float(loss) * count
            total_tokens += count

    if total_tokens == 0 or not math.isfinite(total_loss):
        raise SystemExit("Avaliação inválida: nenhuma previsão finita foi calculada.")

    mean_loss = total_loss / total_tokens
    print(json.dumps({
        "checkpoint": str(checkpoint_path),
        "evaluation_file": str(data_path),
        "parameters": sum(p.numel() for p in model.parameters()),
        "heldout_token_count": total_tokens,
        "heldout_mean_loss": round(mean_loss, 6),
        "heldout_perplexity": round(math.exp(min(mean_loss, 50)), 6),
        "warning": "Métrica de previsão neste pequeno conjunto separado; não mede inteligência geral nem compara modelos."
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
