# LÚMEN AI CORE

Primeiro núcleo funcional do LÚMEN: uma aplicação web adaptada para celular, com API Python e memória persistente em SQLite.

## O que já funciona nesta versão

- Interface em português com abas para conversa, memória, conhecimento, tarefas e histórico.
- Memórias persistidas no banco SQLite do servidor, com categoria e exclusão.
- Base de conhecimento com título, conteúdo e campo de fonte.
- Tarefas com estados pendente, em andamento e concluída.
- Registro de eventos importantes.\n- Histórico persistente das conversas: mensagens do usuário e respostas do modelo ficam salvas e as últimas 20 entram no contexto das próximas conversas.
- Integração opcional com uma API compatível com OpenAI para conversação. Sem chave, o sistema informa que o modelo não está conectado, em vez de simular inteligência.
- Proteção da API por token configurado no servidor.
- Testes automatizados para saúde, autenticação, memória e tarefas.

## Executar localmente

Requisitos: Python 3.11 ou superior.

    cd lumen-ai-core
    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env

Defina no ambiente os valores de `LUMEN_ACCESS_TOKEN` e, se quiser conversação por IA, `OPENAI_API_KEY`. Carregue as variáveis do arquivo .env com seu gerenciador de ambiente e execute:

    uvicorn app:app --host 127.0.0.1 --port 8000

Abra http://127.0.0.1:8000 e informe o token configurado no servidor.

No Windows, ative o ambiente com `.venv\\Scripts\\activate`.

## Testes

    pip install httpx
    python -m unittest discover -s tests -v

## Variáveis de ambiente

| Variável | Função |
|---|---|
| LUMEN_ACCESS_TOKEN | Token obrigatório para proteger a API |
| OPENAI_API_KEY | Chave do provedor de IA, mantida apenas no servidor |
| OPENAI_MODEL | Modelo usado pelo endpoint de chat |
| OPENAI_BASE_URL | URL base de uma API compatível com OpenAI |
| LUMEN_DB_PATH | Caminho do banco SQLite |

## Segurança e limites atuais

- Não publique o servidor sem configurar um token forte e HTTPS.
- Não coloque chaves de API no HTML, no Git ou no aplicativo cliente.
- Esta primeira versão não tem cadastro multiusuário, recuperação de senha nem permissões granulares.
- A memória é persistente no banco do servidor, mas não é ilimitada. Faça backups do arquivo SQLite.
- O servidor não executa tarefas arbitrárias no dispositivo nem opera em segundo plano por conta própria.
- Voz, visão, pesquisa web com fontes, agendamento e automações externas ainda não foram implementados.
- As conversas ficam registradas separadamente da memória pessoal; isso preserva continuidade sem transformar automaticamente cada mensagem em fato sobre o usuário.
- A conexão com o modelo depende da chave e da disponibilidade do provedor configurado.

## Estrutura

- `app.py`: API, banco de dados, autenticação e integração com modelo.
- `index.html`: interface web responsiva.
- `tests/`: testes básicos do núcleo.
