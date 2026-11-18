"""Teste de inferência do checkpoint LÚMEN-1."""
import argparse, torch
from model import LumenGPT, encode, decode
p=argparse.ArgumentParser(); p.add_argument("--model",required=True); p.add_argument("--prompt",default="LÚMEN:"); p.add_argument("--tokens",type=int,default=160); a=p.parse_args()
ckpt=torch.load(a.model,map_location="cpu",weights_only=False)
m=LumenGPT(**ckpt["config"]); m.load_state_dict(ckpt["state_dict"]); m.eval()
x=torch.tensor([encode(a.prompt)],dtype=torch.long)
print(decode(m.generate(x,max_new_tokens=a.tokens)[0].tolist()))
