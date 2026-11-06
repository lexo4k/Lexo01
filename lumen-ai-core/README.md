# LÚMEN AI CORE

Núcleo experimental de IA com memória, planejamento cognitivo e pesquisa web com fontes. Interface em português, adaptada para celular, API Python e banco SQLite.

## Capacidades implementadas

- Conversação com modelo externo compatível com a API OpenAI.
- Memória pessoal explícita e base de conhecimento persistidas em SQLite.
- Histórico de conversas, tarefas e diário de atividade.
- Ciclo cognitivo limitado: compreensão do objetivo, planejamento estruturado e avaliação independente do plano.
- Pesquisa web pelo endpoint `POST /api/research`, usando a ferramenta `web_search` da API OpenAI Responses. Retorna síntese e links das fontes encontradas.
- Interface centrada na conversa: o chat é a tela inicial e os demais recursos ficam recolhidos em um menu secundário. Pedidos explícitos de pesquisa e perguntas sobre fatos atuais podem acionar a pesquisa web dentro da mesma conversa.
- PWA instalável em navegadores compatíveis, com manifesto, ícone e cache limitado da interface para abertura offline. As operações de IA exigem conexão.
- Histórico persistente de conversas e pesquisas, incluindo as fontes consultadas.
- Endpoint de capacidades para distinguir recursos implementados de recursos configurados.
- Possibilidade de arquivar uma pesquisa e suas fontes na base de conhecimento.
- Proteção dos endpoints privados por token.
- Testes automatizados, incluindo validação do endpoint de pesquisa sem credencial.

## Pesquisa na web

A pesquisa integrada envia a pergunta ao servidor. O servidor chama a API Responses com a ferramenta `web_search`, recolhe as citações/URLs devolvidas e apresenta os links para consulta. Uma pesquisa só é considerada realizada quando o provedor responde com sucesso; o sistema não simula resultados.

Requer uma chave de API com acesso à API Responses e à ferramenta `web_search`. Modelos e provedores compatíveis apenas com Chat Completions podem não oferecer essa ferramenta. Se o provedor retornar erro, a interface apresenta a falha em vez de inventar fontes.

## Executar localmente

Requisitos: Python 3.11 ou superior.

    cd lumen-ai-core
    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env

Configure no ambiente do servidor:
- `LUMEN_ACCESS_TOKEN`: token forte para proteger a API.
- `OPENAI_API_KEY`: chave mantida somente no servidor.
- `OPENAI_MODEL`: modelo de conversa e planejamento.
- `LUMEN_RESEARCH_MODEL`: opcional; modelo usado na pesquisa web, por padrão `gpt-4.1`.
- `OPENAI_BASE_URL`: opcional, padrão `https://api.openai.com/v1`. A pesquisa web exige compatibilidade com a API Responses e a ferramenta `web_search`.

Execute:

    uvicorn app:app --host 127.0.0.1 --port 8000

Abra http://127.0.0.1:8000 e informe o token configurado no servidor.

## Testes

    pip install -r requirements.txt
    python -m unittest discover -s tests -v

## Variáveis de ambiente

| Variável | Função |
|---|---|
| LUMEN_ACCESS_TOKEN | Token obrigatório para proteger a API |
| OPENAI_API_KEY | Chave do provedor, mantida apenas no servidor |
| OPENAI_MODEL | Modelo usado na conversa e no planejamento |
| LUMEN_RESEARCH_MODEL | Modelo opcional para pesquisa web |
| OPENAI_BASE_URL | URL base do provedor compatível |
| LUMEN_DB_PATH | Caminho do banco SQLite |

## Segurança, limites e honestidade operacional

- Não publique o servidor sem token forte e HTTPS.
- Nunca coloque chaves no HTML, no Git ou no aplicativo cliente.
- O ciclo cognitivo planeja e avalia, mas não executa ações externas automaticamente.
- Pesquisa web depende de chave, acesso ao serviço Responses e disponibilidade da ferramenta `web_search`.
- A interface PWA pode abrir offline, mas chat, pesquisa, memória sincronizada e voz online exigem servidor e conexão.
- O projeto não inclui anúncios ativos: publicidade exige conta de editor, aprovação e integração com uma rede. Não há anúncios simulados.
- Memórias não são ilimitadas. Faça backups do banco SQLite.
- O sistema não opera em segundo plano depois que a sessão termina.
- Voz e visão dependem do navegador e do modelo configurado; automações externas e execução geral de ferramentas ainda não estão implementadas.
- O modelo configurado é um serviço externo. Este projeto não copia nem transforma o ChatGPT em uma instância independente.
- Conversas ficam separadas das memórias explícitas para evitar transformar automaticamente cada mensagem em fato pessoal.

## Estrutura

- `app.py`: API, autenticação, armazenamento, chat, planejamento e endpoint de pesquisa web.
- `cognition.py`: ciclo de planejamento e avaliação cognitiva.
- `index.html`: interface web responsiva.
- `tests/`: testes automatizados.
