"""Avaliação reproduzível e básica do checkpoint LÚMEN-1."""
import json, math, sys, torch
from pathlib import Path
from model import LumenGPT, encode

def main():
    ckpt_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("artifacts/lumen-1.pt")
    ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    cfg = ckpt["config"]
    model = LumenGPT(**cfg)
    model.load_state_dict(ckpt["state_dict"])
    model.eval()
    corpus = Path("corpus").rglob("*.txt")
    samples = []
    for file in corpus:
        samples.append(file.read_text(encoding="utf-8"))
    if not samples:
        raise SystemExit("No evaluation text found")
    data = torch.tensor(encode("\n".join(samples)), dtype=torch.long)
    context = min(cfg["context"], max(8, len(data)-1))
    x = data[:context].unsqueeze(0)
    y = data[1:context+1].unsqueeze(0)
    with torch.no_grad():
        logits, loss = model(x, y)
    if not torch.isfinite(loss):
        raise SystemExit("Non-finite loss")
    result = {
        "checkpoint": str(ckpt_path),
        "parameters": sum(p.numel() for p in model.parameters()),
        "evaluation_loss_on_seed_text": round(float(loss), 5),
        "logits_shape": list(logits.shape),
        "warning": "Seed-text loss is a smoke metric, not a benchmark of general intelligence."
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
if __name__ == "__main__":
    main()
