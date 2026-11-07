"""Treinamento reproduzível de LÚMEN-1 com retomada de checkpoint."""
from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path

import torch
from model import LumenGPT, encode


def load_corpus(source: Path) -> tuple[list[Path], torch.Tensor]:
    files = [source] if source.is_file() else sorted(source.rglob("*.txt"))
    if not files:
        raise SystemExit("Nenhum arquivo .txt encontrado.")
    content = "\n\n".join(path.read_text(encoding="utf-8") for path in files)
    return files, torch.tensor(encode(content), dtype=torch.long)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="Arquivo .txt ou diretório com .txt")
    parser.add_argument("--out", default="artifacts/lumen-1.pt")
    parser.add_argument("--steps", type=int, default=2000, help="Número total de passos desejado")
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--context", type=int, default=256)
    parser.add_argument("--width", type=int, default=256)
    parser.add_argument("--layers", type=int, default=6)
    parser.add_argument("--heads", type=int, default=8)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--save-every", type=int, default=250)
    parser.add_argument("--resume", action="store_true", help="Retoma pesos e otimizador do --out")
    args = parser.parse_args()

    if min(args.steps, args.batch, args.context, args.width, args.layers, args.heads, args.save_every) <= 0:
        raise SystemExit("steps, batch, context, width, layers, heads e save-every precisam ser positivos.")
    if args.width % args.heads:
        raise SystemExit("width precisa ser divisível por heads.")

    random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)

    files, tokens = load_corpus(Path(args.data))
    if len(tokens) < args.context * 2 + 2:
        raise SystemExit("Corpus muito pequeno: aumente os textos ou reduza context.")
    split = int(len(tokens) * 0.9)
    train_tokens, valid_tokens = tokens[:split], tokens[split:]
    if len(valid_tokens) < args.context + 2:
        raise SystemExit("A partição de validação precisa conter pelo menos context+2 tokens.")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    config = {"width": args.width, "layers": args.layers, "heads": args.heads, "context": args.context}
    model = LumenGPT(**config).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, betas=(0.9, 0.95), weight_decay=0.1)
    start_step = 0
    output = Path(args.out)

    if args.resume:
        if not output.is_file():
            raise SystemExit(f"Não há checkpoint para retomar: {output}")
        saved = torch.load(output, map_location=device, weights_only=False)
        if saved.get("config") != config:
            raise SystemExit("A configuração do modelo não corresponde ao checkpoint.")
        model.load_state_dict(saved["state_dict"])
        if "optimizer_state_dict" in saved:
            optimizer.load_state_dict(saved["optimizer_state_dict"])
        start_step = int(saved.get("step", 0))
        print(json.dumps({"event": "resume", "from_step": start_step, "checkpoint": str(output)}))

    def sample_batch(data: torch.Tensor):
        starts = torch.randint(0, len(data) - args.context - 1, (args.batch,))
        x = torch.stack([data[i:i + args.context] for i in starts]).to(device)
        y = torch.stack([data[i + 1:i + args.context + 1] for i in starts]).to(device)
        return x, y

    def validation_loss() -> float:
        model.eval()
        # Avaliação determinística em janelas fixas, sem amostragem aleatória.
        losses, counts = 0.0, 0
        with torch.no_grad():
            for offset in range(0, len(valid_tokens) - args.context - 1, args.context):
                x = valid_tokens[offset:offset + args.context].unsqueeze(0).to(device)
                y = valid_tokens[offset + 1:offset + args.context + 1].unsqueeze(0).to(device)
                _, loss = model(x, y)
                losses += float(loss) * y.numel()
                counts += y.numel()
        return losses / max(counts, 1)

    best_valid = float("inf")
    if args.resume and output.exists():
        best_valid = float(saved.get("best_validation_loss", best_valid))

    def save_checkpoint(step: int, valid: float, best: float):
        output.parent.mkdir(parents=True, exist_ok=True)
        torch.save({
            "state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "config": config,
            "vocab": "utf8-byte-256+eos",
            "training_files": [str(path) for path in files],
            "training_tokens": len(train_tokens),
            "validation_tokens": len(valid_tokens),
            "step": step,
            "best_validation_loss": best,
            "last_validation_loss": valid,
            "seed": args.seed,
        }, output)

    for step in range(start_step + 1, args.steps + 1):
        model.train()
        x, y = sample_batch(train_tokens)
        _, loss = model(x, y)
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        grad_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()

        if step == 1 or step % 100 == 0 or step == args.steps:
            valid = validation_loss()
            best_valid = min(best_valid, valid)
            save_checkpoint(step, valid, best_valid)
            print(json.dumps({
                "step": step,
                "target_steps": args.steps,
                "train_loss": round(float(loss), 5),
                "validation_loss": round(valid, 5),
                "best_validation_loss": round(best_valid, 5),
                "gradient_norm": round(float(grad_norm), 5),
                "device": device,
                "checkpoint": str(output),
            }, ensure_ascii=False))

        elif step % args.save_every == 0:
            save_checkpoint(step, float("nan"), best_valid)

    if start_step >= args.steps:
        print(json.dumps({"event": "already_at_target", "step": start_step, "target_steps": args.steps}))
    else:
        print(f"Checkpoint salvo em {output}; passos={args.steps}; tokens={len(tokens)}")


if __name__ == "__main__":
    main()
