# AURION + Minecraft Bedrock Android

## Status desta entrega

Foi adicionado um primeiro caminho executável de integração para **Bedrock Dedicated Server (BDS)**:

- behavior pack com Script API estável e formulário \`@minecraft/server-ui\` para capturar uma mensagem digitada ao interagir com um NPC identificado;
- companion Python no host BDS que lê o evento estruturado no console do servidor, encaminha-o ao relay HTTPS e entrega a resposta recebida com \`tellraw\`;
- painel de pareamento no APK AURION, que carrega o GGUF local antes de gerar o código;
- polling Android limitado ao período em que AURION está em primeiro plano;
- testes de contrato e empacotamento do behavior pack em CI.

Isso ainda não é uma integração validada dentro do jogo. O relay não está implantado, não houve execução de BDS nem teste com o Minecraft Android real nesta execução.

## Limite de plataforma

A documentação oficial da Microsoft declara que \`@minecraft/server-net\` só funciona no Bedrock Dedicated Server e não funciona no cliente do jogo nem no Minecraft Realms. O módulo está em pré-lançamento e a versão documentada atualmente é específica de uma build Preview. Por isso, o pack desta entrega **não depende de \`@minecraft/server-net\`**.

O pack usa somente \`@minecraft/server\` e escreve um marcador estruturado no console do BDS. O companion Python, executado no mesmo host do BDS, faz o tráfego HTTPS com o relay. Isso evita fingir que um behavior pack comum pode abrir HTTP no mundo local do Android. A documentação oficial de scripts multiplayer também esclarece que os scripts do Bedrock executam no lado do servidor, não no cliente; as definições `client_entity` de resource packs tratam da apresentação visual, não criam uma ponte de rede executável dentro do app Android. Portanto, não há uma ponte client-side oficial suportada que substitua o BDS neste desenho. [Documentação de scripts multiplayer](https://learn.microsoft.com/en-us/minecraft/creator/documents/scripting/multiplayer-scripts?view=minecraft-bedrock-stable).

O caminho mantém o aplicativo oficial Minecraft Bedrock Android como cliente do jogo, mas exige que ele entre em um mundo hospedado por BDS compatível. **Mundo local de um jogador e Realms não são suportados por esta arquitetura.**

Fontes oficiais:
- [Módulo @minecraft/server-net e limite BDS/cliente/Realms](https://learn.microsoft.com/en-us/minecraft/creator/scriptapi/minecraft/server-net/minecraft-server-net)
- [Script API para Bedrock Dedicated Server](https://learn.microsoft.com/en-us/minecraft/creator/documents/bedrockserver/scripting?view=minecraft-bedrock-stable)
- [Ajuda oficial de configuração do BDS, clientes móveis e compatibilidade](https://help.minecraft.net/hc/en-us/articles/49914677714957)

## Compatibilidade e versão

- Manifesto do pack: \`min_engine_version = 1.26.60\`.
- Dependências de script: \`@minecraft/server\` 2.0.0 e \`@minecraft/server-ui\` 2.0.0, ambas estáveis.
- O servidor BDS precisa usar uma versão compatível com a versão instalada do cliente Bedrock Android. A Microsoft alerta que versões de protocolo diferentes podem impedir a conexão.
- A ajuda oficial consultada em 2026-11-12 orienta BDS 26.60 ou mais novo para a mudança de transporte NetherNet e informa que o servidor oficial está disponível para Windows 64-bit e Ubuntu Linux, não para hosts ARM.
- A versão exata do Minecraft instalada no telefone do usuário não está disponível nesta execução. Portanto, a compatibilidade final do manifesto ainda precisa ser confirmada com a versão real do cliente e do BDS.

Não ative o pack em um mundo importante sem backup. A configuração e a instalação do pack precisam ser feitas no mundo hospedado pelo BDS.

## Componentes adicionados

### Behavior pack

\`behavior-pack/\` captura \`world.afterEvents.playerInteractWithEntity\`. Ele considera NPCs nativos e entidades com `nameTag` não vazio. Antes de emitir o evento, atribui à entidade a propriedade dinâmica `aurion:npc_identity`; o valor fica salvo nos dados do mundo e mantém a identidade do mesmo NPC após reinicializações do BDS, permitindo que a memória local do AURION continue associada a ele. Se a API não permitir ler ou gravar a propriedade, o script usa o ID de runtime com prefixo `runtime-` e registra um aviso. Nesse fallback a identidade pode mudar após a recriação da entidade, portanto a persistência não é garantida. Ao interagir, abre um formulário estável `ModalFormData` com um campo de texto. Depois do envio, o evento \`chat\` contém a mensagem digitada, jogador, nome, ID da entidade (npc_id), tipo (npc_type), mundo e ID de correlação. Um limite de 15 segundos por jogador reduz spam. O formulário evita depender do evento de chat Preview.

O script não envia HTTP, não guarda tokens e não cria respostas fictícias.

### Companion do host BDS

\`host/aurion_bds_host.py\`:

1. recebe o código de uso único mostrado pelo AURION;
2. reivindica o pareamento no relay e salva o token do lado do servidor em arquivo local privado;
3. verifica e ajusta \`server.properties\` antes de iniciar o BDS: define \`content-log-console-output-enabled=true\` e \`content-log-level=warning\`, necessários para que os \`console.warn()\` do Script API cheguem ao stdout; se houver alteração, cria uma cópia \`server.properties.aurion-backup-*\` e preserva as demais configurações;
4. inicia o executável oficial BDS na pasta indicada;
5. lê os eventos emitidos pelo behavior pack no console;
5. encaminha eventos ao relay e consulta respostas;
6. entrega cada resposta ao jogador associado por meio de um comando \`tellraw\` enviado ao console do BDS.

O token do servidor nunca entra no behavior pack. Em sistemas POSIX, o arquivo de credenciais é criado com permissão \`0600\`. No Windows, mantenha o arquivo na pasta privada da conta que executa o BDS.

Exemplo de inicialização:

\`\`\`bash
python minecraft-bedrock/host/aurion_bds_host.py \
  --server-dir "/caminho/para/bedrock-server" \
  --relay-url "https://SEU-RELAY-HTTPS" \
  --pairing-code "12345678"
\`\`\`

O companion inicia o BDS por conta própria. Na primeira inicialização, ativa automaticamente a saída dos content logs no console, pois o padrão do BDS pode manter essa saída desativada e impedir a captura dos marcadores \`AURION_EVENT\`. A configuração original é copiada para \`server.properties.aurion-backup-*\` antes da alteração. Não abra outra instância do mesmo servidor. Para novo pareamento, forneça o novo código em \`--pairing-code\`; sem esse argumento, o companion tenta reutilizar as credenciais salvas.

### Aplicativo Android AURION

Em **Núcleo → Minecraft Bedrock**, informe a URL HTTPS do relay e toque em gerar código. O aplicativo carrega o GGUF local antes de iniciar o pareamento. O token do aplicativo fica criptografado pelo Android Keystore.

AURION consulta o relay a cada três segundos. Ao concluir o pareamento, inicia um foreground service Android com notificação persistente, permitindo que a ponte continue enquanto o cliente Minecraft ocupa a tela. O polling e a inferência ainda vivem no escopo do processo da Activity, mantido em prioridade de foreground pelo serviço; se o Android encerrar a Activity/processo, a ponte precisa ser retomada ao abrir AURION. No Android 15 (target SDK 35), serviços `dataSync` têm limite de seis horas em 24 horas quando o app está em segundo plano; o callback de timeout interrompe o polling e a próxima abertura do AURION pode retomá-lo. O serviço é encerrado ao desconectar ou fechar a tarefa do AURION. O aplicativo mantém localmente até seis turnos por combinação de mundo, jogador e identidade da entidade, para preservar contexto sem misturar NPCs. Respostas já geradas também entram em uma pequena caixa de saída local antes do envio, evitando gerar outra fala se uma tentativa de rede falhar. O ciclo em segundo plano ainda não foi validado em aparelho físico.

### Relay

\`relay/\` mantém códigos de pareamento de uso único, tokens separados por lado, isolamento de sessão, deduplicação, filas limitadas e rate limiting.

**Persistência configurável:** o relay agora usa SQLite quando a variável `AURION_RELAY_DB_PATH` aponta para um arquivo. Pairings, sessões, filas, deduplicação e janelas de rate limit sobrevivem a reinicializações do processo; os tokens são armazenados somente como hashes. Em POSIX, o arquivo do banco recebe permissão `0600`. O modo pode ser conferido em `GET /health`: `sqlite_file` ou `memory_ephemeral`.

**Limite de hospedagem:** sem `AURION_RELAY_DB_PATH`, o relay continua em memória. O blueprint Render deste repositório usa o plano gratuito e não declara disco persistente; portanto, ele ainda não oferece retenção durável. Para produção, configure `AURION_RELAY_DB_PATH=/var/data/aurion-minecraft.sqlite3` apontando para um disco persistente privado montado nesse caminho. Não configure apenas um caminho no filesystem efêmero e interprete isso como backup. O banco SQLite não criptografa o conteúdo das filas em repouso, então o volume deve ser privado e protegido. O relay ainda não foi implantado.

O blueprint `minecraft-bedrock/relay/render.yaml` define `AURION_REQUIRE_PERSISTENT_STORAGE=true`. Assim, a implantação Render atual não emite códigos nem aceita reivindicação de pareamento enquanto estiver em armazenamento efêmero: `/health` informa `degraded` e `pairing_available=false`, e os endpoints de pareamento retornam HTTP 503. Isso é intencional; não habilite o relay em produção até montar um volume persistente privado e apontar `AURION_RELAY_DB_PATH` para ele. O plano gratuito sem disco persistente não é tratado como pronto para uso.

## Como o fluxo deve funcionar

1. O Minecraft Bedrock Android entra no mundo BDS compatível.
2. O jogador interage com um NPC nativo ou entidade nomeada.
3. O behavior pack emite o evento real no console do BDS.
4. O companion encaminha o evento ao relay.
5. O APK AURION recebe o evento e chama o mesmo motor local \`Llama.complete\` usado pelo chat.
6. A resposta gerada pelo GGUF retorna ao relay.
7. O companion envia \`tellraw\` ao jogador no mesmo mundo.

A resposta é texto de chat do jogo identificada com o nome do NPC. A memória individual local por entidade está implementada no APK, mas ainda precisa de teste real em duas interações. Ainda não há animação de fala nem voz dentro do Minecraft.

### Entrada de texto do jogador

A entrada de texto usa \`@minecraft/server-ui\` estável 2.0.0 e \`ModalFormData.textField\`. Não usa \`world.beforeEvents.chatSend\`, que ainda aparece como pré-lançamento na documentação consultada, nem exige ativar APIs Preview. O cliente oficial recebe o formulário do próprio servidor; o texto enviado segue como \`event_type = chat\` até o AURION.

Referência: [changelog oficial de @minecraft/server](https://learn.microsoft.com/en-us/minecraft/creator/scriptapi/minecraft/server/changelog?view=minecraft-bedrock-stable).

## CI e testes

O workflow \`.github/workflows/minecraft-relay.yml\` executa os testes do relay, do companion e do contrato do pack, valida a sintaxe JavaScript/Python e publica o arquivo \`.mcpack\` como artefato. O workflow Android valida o APK separadamente.

Essas verificações não substituem o teste de compatibilidade dentro do cliente oficial.

## Critérios ainda pendentes

- implantação do relay com armazenamento durável e URL HTTPS real;
- host x64 com BDS oficial e versão compatível com o cliente do telefone;
- ativação do behavior pack no mundo BDS;
- conexão do Minecraft Android oficial ao mundo;
- confirmação de que uma interação real aparece no console e chega ao AURION;
- confirmação de que o GGUF real gera texto não padronizado;
- confirmação de que a resposta retorna ao jogador no mesmo mundo;
- segunda interação demonstrando memória/contexto do NPC;
- teste separado da voz Android, sem alegar que o áudio sai pelo Minecraft.

Nenhum desses critérios de execução física é marcado como concluído apenas por passar CI ou gerar um \`.mcpack\`/APK.
