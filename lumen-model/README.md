# LÚMEN-1: modelo experimental próprio

Este diretório contém uma arquitetura Transformer causal criada para o projeto LÚMEN,
com pesos inicializados do zero e tokenizer UTF-8 byte-level (256 bytes + EOS).
Não carrega pesos de OpenAI, Meta, Google, Mistral ou outros fornecedores.

## Instalar isoladamente
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-model.txt
```
PyTorch é necessário apenas no ambiente de treinamento/inferência, não no backend web.

## Corpus
Coloque arquivos TXT com conteúdo que você criou ou tem autorização para usar em
`corpus/`. Remova dados pessoais, segredos e conteúdo sem licença. O script não
baixa datasets nem envia os arquivos para serviços externos.

## Treinar
```bash
python lumen-model/train.py --data lumen-model/corpus --steps 2000 --context 256 --out lumen-model/artifacts/lumen-1.pt
```
Para um primeiro teste pequeno, use `--steps 20 --width 64 --layers 2 --heads 2 --context 64 --batch 4`.
GPU CUDA acelera bastante; em CPU, mantenha configurações pequenas.

## Testar geração
```bash
python lumen-model/infer.py --model lumen-model/artifacts/lumen-1.pt --prompt "LÚMEN:"
```

## Limites importantes
Este é o primeiro modelo-base experimental, não um assistente geral comparável a
modelos comerciais. Um Transformer pequeno treinado com pouco texto aprende padrões
limitados e pode produzir respostas incoerentes. Qualidade exige corpus amplo,
legalmente utilizável, limpeza, avaliação, treinamento longo e hardware adequado.
O código não declara o modelo treinado: só existe checkpoint depois de executar
o treinamento com corpus real. O modelo ainda não está conectado ao endpoint /api/chat.
