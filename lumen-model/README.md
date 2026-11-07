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

## Retomar treinamento

O checkpoint guarda pesos, estado do otimizador, configuração e número de passos. Para continuar um treinamento interrompido, mantenha os mesmos parâmetros de arquitetura e execute:

```bash
python lumen-model/train.py --data lumen-model/corpus --steps 5000 --context 256 --width 256 --layers 6 --heads 8 --batch 16 --out lumen-model/artifacts/lumen-1.pt --resume
```

`--steps` representa o total de passos desejado, não passos adicionais. O treinamento registra validação determinística e salva checkpoints periodicamente. Use somente textos próprios ou com licença compatível.

## Testar geração
```bash
python lumen-model/infer.py --model lumen-model/artifacts/lumen-1.pt --prompt "LÚMEN:"
```

## Avaliação independente

O arquivo `evaluation/heldout-pt-br.txt` é mantido separado de `corpus/` e não entra no treinamento. Execute `python lumen-model/evaluate.py lumen-model/artifacts/lumen-1.pt --data lumen-model/evaluation/heldout-pt-br.txt` para obter perda média e perplexidade em texto reservado. Essas métricas medem previsão nesse conjunto pequeno, não inteligência geral nem superioridade sobre outros modelos.

## Limites importantes
Este é o primeiro modelo-base experimental, não um assistente geral comparável a
modelos comerciais. Um Transformer pequeno treinado com pouco texto aprende padrões
limitados e pode produzir respostas incoerentes. Qualidade exige corpus amplo,
legalmente utilizável, limpeza, avaliação, treinamento longo e hardware adequado.
O código não declara o modelo treinado: só existe checkpoint depois de executar
o treinamento com corpus real. O modelo ainda não está conectado ao endpoint /api/chat.
