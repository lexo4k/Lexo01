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
| LUMEN_DB_PATH | Caminho do banco SQLite quando PostgreSQL não está configurado |\n| DATABASE_URL | URL privada de conexão PostgreSQL; opcional |

## Segurança, limites e honestidade operacional

- Não publique o servidor sem token forte e HTTPS.
- Nunca coloque chaves no HTML, no Git ou no aplicativo cliente.
- O ciclo cognitivo planeja e avalia, mas não executa ações externas automaticamente.
- Pesquisa web depende de chave, acesso ao serviço Responses e disponibilidade da ferramenta `web_search`.
- A interface PWA pode abrir offline, mas chat, pesquisa, memória sincronizada e voz online exigem servidor e conexão.
- O projeto não inclui anúncios ativos: publicidade exige conta de editor, aprovação e integração com uma rede. Não há anúncios simulados.
- Memórias não são ilimitadas. SQLite guarda os dados no disco configurado e pode perder dados em instâncias efêmeras. Para persistência gerenciada, configure `DATABASE_URL` com um PostgreSQL compatível e mantenha backups. A aplicação não cria uma conta de banco nem provisiona o banco externo automaticamente.
- O sistema não opera em segundo plano depois que a sessão termina.
- Voz e visão dependem do navegador e do modelo configurado; automações externas e execução geral de ferramentas ainda não estão implementadas.
- O modelo configurado é um serviço externo. Este projeto não copia nem transforma o ChatGPT em uma instância independente.
- Conversas ficam separadas das memórias explícitas para evitar transformar automaticamente cada mensagem em fato pessoal.


## Publicar no Render

O arquivo `render.yaml` já define o serviço Docker e a rota de saúde. Para publicar:

1. Entre no Render e escolha **New → Blueprint**.
2. Selecione o repositório `lexo4k/Lexo01` e a branch `lumen-ai-core`.
3. Confirme o serviço `lumen-ai-core`. O diretório raiz é `lumen-ai-core`.
4. No painel do serviço, preencha `OPENAI_API_KEY` com uma chave válida do provedor. A chave deve ficar somente no ambiente do servidor.
5. Aguarde o deploy e confira `https://SEU-DOMINIO/api/health`. O campo `model_connected` precisa aparecer como `true`.
6. Use o valor gerado para `LUMEN_ACCESS_TOKEN` no formulário **Conectar ao núcleo**.

O deploy não pode ser concluído por este repositório sozinho: é necessário autorizar a criação do serviço na conta Render e fornecer uma credencial válida do provedor. O plano gratuito não oferece disco persistente para SQLite. O núcleo agora também aceita PostgreSQL por `DATABASE_URL`: crie um banco gerenciado (por exemplo, um PostgreSQL externo compatível), copie a URL de conexão para a variável `DATABASE_URL` no ambiente do serviço Render e faça um novo deploy. Quando essa variável existe, o app usa PostgreSQL; sem ela, continua usando SQLite. A criação do banco e a inclusão da URL ainda exigem acesso à conta do provedor. Não cole a URL em código público.

## Aplicativo Android

A interface entregue nesta branch é um PWA instalável pelo navegador Android depois que o servidor estiver publicado em HTTPS: abra o endereço do serviço no Chrome e use **Instalar app** ou **Adicionar à tela inicial**, conforme a opção exibida pelo navegador.

Agora existe também o módulo Android próprio em `lumen-android/`. Ele abre a interface HTTPS do núcleo em um WebView seguro, permite escolher imagem e guarda o endereço do servidor no aparelho. O endereço do servidor é solicitado na primeira abertura porque ainda não há uma instância Render publicada. O workflow dedicado `LÚMEN Android APK` compila somente o módulo `:lumen` e publica o artefato `Lumen-AI-debug` por 14 dias. Abra a aba Actions do GitHub, selecione a execução mais recente desse workflow, aguarde `success` e baixe o artefato `Lumen-AI-debug`. O workflow antigo `Build Android APKs` continua separado para os demais aplicativos do repositório. O APK é um cliente Android do núcleo web, não contém um modelo de IA offline.

## Estado real da entrega

- Código e interface PWA: presentes nesta branch.
- Testes automatizados do núcleo: aprovados no GitHub Actions (run 42313671953).
- Serviço público Render: ainda não criado/publicado por esta entrega.
- IA e pesquisa web: implementadas, mas só ficam operacionais após configurar a chave do provedor no servidor.
- Memória durável hospedada: depende de disco persistente ou banco gerenciado; o plano gratuito com disco efêmero não garante retenção.
- APK próprio do LÚMEN: módulo Android criado; compilação e artefato `Lumen-AI-debug` dependem da conclusão bem-sucedida do workflow Android mais recente.
- Anúncios: não integrados; exigem conta de editor e aprovação em uma rede de anúncios.

## Estrutura

- `app.py`: API, autenticação, armazenamento, chat, planejamento e endpoint de pesquisa web.
- `cognition.py`: ciclo de planejamento e avaliação cognitiva.
- `index.html`: interface web responsiva.
- `lumen-android/`: aplicativo Android nativo que conecta ao servidor HTTPS.
- `tests/`: testes automatizados.
