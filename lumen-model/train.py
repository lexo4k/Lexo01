"""Treinamento local de LÚMEN-1 a partir de arquivos .txt próprios/licenciados."""
from __future__ import annotations
import argparse, json, math, random
from pathlib import Path
import torch
from model import LumenGPT, encode, decode

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--data", required=True, help="Arquivo .txt ou diretório com .txt")
    p.add_argument("--out", default="artifacts/lumen-1.pt")
    p.add_argument("--steps", type=int, default=2000)
    p.add_argument("--batch", type=int, default=16)
    p.add_argument("--context", type=int, default=256)
    p.add_argument("--width", type=int, default=256)
    p.add_argument("--layers", type=int, default=6)
    p.add_argument("--heads", type=int, default=8)
    p.add_argument("--lr", type=float, default=3e-4)
    p.add_argument("--seed", type=int, default=17)
    a=p.parse_args()
    random.seed(a.seed); torch.manual_seed(a.seed)
    source=Path(a.data)
    files=[source] if source.is_file() else sorted(source.rglob("*.txt"))
    if not files: raise SystemExit("Nenhum arquivo .txt encontrado.")
    text="\n\n".join(f.read_text(encoding="utf-8") for f in files)
    tokens=torch.tensor(encode(text), dtype=torch.long)
    if len(tokens) < a.context+2: raise SystemExit("Corpus muito pequeno para o context escolhido.")
    split=int(len(tokens)*0.9); train=tokens[:split]; valid=tokens[split:]
    if len(valid)<a.context+2: valid=train
    device="cuda" if torch.cuda.is_available() else "cpu"
    model=LumenGPT(a.width,a.layers,a.heads,a.context).to(device)
    opt=torch.optim.AdamW(model.parameters(),lr=a.lr)
    def batch(data):
        starts=torch.randint(0,len(data)-a.context-1,(a.batch,))
        x=torch.stack([data[i:i+a.context] for i in starts]).to(device)
        y=torch.stack([data[i+1:i+a.context+1] for i in starts]).to(device)
        return x,y
    for step in range(1,a.steps+1):
        model.train(); x,y=batch(train); _,loss=model(x,y)
        opt.zero_grad(set_to_none=True); loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(),1.0); opt.step()
        if step==1 or step%100==0:
            model.eval()
            with torch.no_grad():
                vx,vy=batch(valid); _,vl=model(vx,vy)
            print(json.dumps({"step":step,"train_loss":round(loss.item(),4),"validation_loss":round(vl.item(),4),"device":device}))
    out=Path(a.out); out.parent.mkdir(parents=True,exist_ok=True)
    torch.save({"state_dict":model.state_dict(),"config":{"width":a.width,"layers":a.layers,"heads":a.heads,"context":a.context},"vocab":"utf8-byte-256+eos","training_files":[str(f) for f in files]},out)
    print(f"Modelo salvo em {out}; bytes de treino={len(tokens)}")
if __name__=="__main__": main()
