# AURION AI CORE

Núcleo experimental de IA com memória, planejamento cognitivo e pesquisa web com fontes. Interface em português, adaptada para celular, API Python e banco SQLite.

## Capacidades implementadas

- Conversação com modelo externo compatível com a API OpenAI.
- Interface Android e web com modos separados de conversa, pesquisa web e planejamento cognitivo.
- Entrada de voz quando o navegador oferece reconhecimento de fala; leitura das respostas em voz alta.
- Análise de imagens JPEG, PNG e WebP com envio ao modelo configurado.
- Sincronização idempotente de memórias, tarefas e conhecimentos locais com a API autenticada, evitando duplicações por conteúdo.
- Memória pessoal explícita e base de conhecimento persistidas em SQLite.
- Memória de correções técnicas com causa-raiz, solução, ambiente, evidência de testes, status pendente/verificado e busca priorizando soluções verificadas. Endpoints: `GET /api/corrections`, `POST /api/corrections` e `GET /api/corrections/search?q=...`.
- Aprendizado controlado por feedback explícito: cada resposta pode ser avaliada como útil ou pouco útil; experiências positivas com uma lição são incluídas como contexto futuro, enquanto avaliações negativas ficam para revisão. Endpoints: `GET /api/experiences` e `POST /api/experiences`. Isso não altera automaticamente os pesos do modelo nem permite autoedição do código.
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
## API própria AURION (gateway multi-provedor)

O núcleo agora expõe um contrato público inspirado em **OpenAI Chat Completions**, hospedado no domínio do AURION. Aplicativos e agentes podem chamar `GET /v1/models` e `POST /v1/chat/completions` usando o token do AURION no cabeçalho `Authorization: Bearer SEU_TOKEN`. O identificador do modelo segue `provedor/modelo`, por exemplo `openai/gpt-4.1-mini`.

Os provedores são cadastrados pela variável de ambiente `AURION_PROVIDERS (compatível também com NEXORA_PROVIDERS legado)` (JSON). Cada entrada informa `base_url`, `api_key_env` e a lista permitida em `models`. `api_key_env` contém somente o nome da variável secreta; o valor real fica no ambiente privado do Render, nunca no código, no app Android ou no Git. A primeira versão encaminha o protocolo OpenAI Chat Completions para provedores que implementam esse formato. Não promete compatibilidade universal: APIs proprietárias com protocolos diferentes, streaming, áudio e formatos multimodais específicos exigem adaptadores próprios. O gateway rejeita streaming nesta versão e valida a estrutura básica da resposta upstream. Cada provedor pode declarar `fallbacks` com IDs `provedor/modelo` que também estejam na lista permitida. Se o principal falhar, o gateway tenta os alternativos na ordem definida e informa o modelo realmente usado. `GET /v1/providers` mostra o estado do catálogo sem revelar segredos.

Exemplo de chamada:

```bash
curl https://SEU-DOMINIO/v1/chat/completions \\
  -H 'Authorization: Bearer SEU_TOKEN' \\
  -H 'Content-Type: application/json' \\
  -d '{"model":"openai/gpt-4.1-mini","messages":[{"role":"user","content":"Olá, AURION"}]}'
```

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

## Memória de correções e evolução controlada

O chat apresenta controles de avaliação nas respostas. Uma avaliação positiva é guardada como experiência útil somente quando acompanhada de uma lição; ela pode orientar respostas futuras nos modos de modelo próprio e provedor externo. Uma avaliação negativa é arquivada para revisão e não é usada como exemplo positivo. O usuário pode consultar as experiências em `GET /api/experiences`. Esse mecanismo é memória contextual com feedback, não treinamento automático dos pesos do modelo. Para treinamento real, seria necessário um pipeline separado de coleta consentida, curadoria, avaliação, fine-tuning e implantação versionada.

A memória técnica registra assinaturas de erro, causa-raiz, resolução, ambiente e evidências de teste. Uma solução só é marcada como verificada quando o registro inclui `tests_passed=true` e evidência; a busca prioriza esses registros. O sistema reutiliza a experiência como referência, mas não altera arquivos de produção nem publica código por conta própria. Correções de código continuam sujeitas a CI, revisão e rollback.

A memória técnica usa o mesmo banco da aplicação. No serviço Render atual, sem PostgreSQL gerenciado ou disco persistente, o SQLite está em armazenamento efêmero e pode ser perdido quando a instância reinicia ou é recriada. Não trate isso como backup permanente. Para retenção durável, é necessário conectar um banco PostgreSQL com plano e política de retenção adequados e fazer backups.

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

Agora existe também o módulo Android próprio em `lumen-android/`. O APK inclui uma cópia local da interface completa: início, conversa, pesquisa web, planejamento, entrada/saída de voz, análise de imagem, memórias, tarefas, base de conhecimento, configurações e importação/exportação JSON. A permissão de microfone só é solicitada quando a entrada de voz é acionada e o Android WebView oferece captura de áudio. A organização local funciona sem servidor e os registros ficam no armazenamento do aplicativo. A conversa aberta com um modelo de IA, pesquisa web e sincronização exigem servidor autenticado e chave de provedor configurada no servidor. O endereço do servidor publicado nesta branch é preenchido automaticamente nas configurações; o token privado ainda precisa ser informado no aparelho. O workflow dedicado `AURION Android APK` compila somente o módulo `:lumen` e publica o artefato `Aurion-AI-debug` por 14 dias. Abra a aba Actions do GitHub, selecione a execução mais recente desse workflow, aguarde `success` e baixe o artefato `Aurion-AI-debug`. O workflow antigo `Build Android APKs` continua separado para os demais aplicativos do repositório. O APK não contém um modelo de IA offline.

## Estado real da entrega

- Código e interface PWA: presentes nesta branch.
- Testes automatizados do núcleo: workflow `AURION Core Tests` executado a cada alteração relevante da branch.
- Serviço público Render: ainda não criado/publicado por esta entrega.
- IA e pesquisa web: implementadas, mas só ficam operacionais após configurar a chave do provedor no servidor.
- Memória durável hospedada: depende de disco persistente ou banco gerenciado; o plano gratuito com disco efêmero não garante retenção.
- APK próprio do LÚMEN: workflow `AURION Android APK` executa os testes de regressão antes de compilar `assembleDebug` e publicar `Aurion-AI-debug`.
- Anúncios: não integrados; exigem conta de editor e aprovação em uma rede de anúncios.

## Estrutura

- `app.py`: API, autenticação, armazenamento, chat, planejamento e endpoint de pesquisa web.
- `cognition.py`: ciclo de planejamento e avaliação cognitiva.
- `index.html`: interface web responsiva.
- `lumen-android/`: aplicativo Android nativo que conecta ao servidor HTTPS.
- `tests/`: testes automatizados.


## Manutenção e atualização contínua

O workflow `AURION Continuous Maintenance` roda a cada seis horas e também a cada alteração relevante da branch. Ele compila os módulos Python, executa os testes automatizados e audita dependências. O Dependabot verifica semanalmente atualizações de bibliotecas Python e GitHub Actions, abrindo pull requests para análise e validação. O Render publica commits da branch automaticamente. Atualizações de dependências não são instaladas às cegas: entram como propostas, passam pelos testes e precisam ser aceitas antes de chegar à produção. Isso reduz o risco de uma atualização quebrar o app ou expor dados.

A lista de provedores é atualizada por configuração do servidor e pode ser consultada em `GET /v1/providers`; o gateway faz failover apenas para modelos alternativos explicitamente cadastrados. APIs nativas incompatíveis precisam de adaptadores próprios. O AURION não descobre credenciais privadas, não cria acesso a satélites, redes ou serviços fechados e não altera hardware remotamente.
