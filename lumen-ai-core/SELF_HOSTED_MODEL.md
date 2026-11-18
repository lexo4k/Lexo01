# LÚMEN CORE: motor próprio e modelo auto-hospedado

O LÚMEN separa três coisas diferentes:

1. **Credencial própria do LÚMEN**: `LUMEN_ACCESS_TOKEN`, criada por nós para proteger a API.
2. **Motor de conversa**: backend LÚMEN, histórico, memória, ferramentas e regras de execução.
3. **Modelo de linguagem**: o componente que gera texto e raciocínio. Pode ser executado por nós com Ollama, sem chave comercial, ou por uma API compatível.

## Gerar credencial própria

No servidor, gere um segredo aleatório forte:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Cadastre o resultado como variável de ambiente `LUMEN_ACCESS_TOKEN`. Nunca coloque esse segredo no Git, em prints ou no código do APK.

## Usar um modelo próprio com Ollama

Instale Ollama em uma máquina/servidor que ficará ligado, baixe um modelo compatível e inicie o serviço. O backend LÚMEN aceita a API compatível do Ollama:

```env
LUMEN_ACCESS_TOKEN=<segredo-gerado-separadamente>
LUMEN_MODEL_BASE_URL=http://SEU-HOST-OLLAMA:11434/v1
LUMEN_MODEL_NAME=llama3.2
```

O Ollama não exige uma chave comercial para a API local. O LÚMEN usa um marcador interno apenas para compatibilidade com o cabeçalho de autorização. Esse marcador **não é uma credencial secreta nem dá acesso ao modelo**.

**Importante:** `localhost` só funciona quando Ollama e backend estão na mesma máquina. Se o backend estiver hospedado na Vercel, não use `localhost`: a Vercel não consegue acessar o Ollama que está no seu celular ou computador. Use um servidor seu acessível pela rede, com HTTPS e autenticação/firewall. Não exponha a porta 11434 diretamente à internet.

## Provedores compatíveis

Também é possível usar `LUMEN_MODEL_API_KEY`, `LUMEN_MODEL_BASE_URL` e `LUMEN_MODEL_NAME` para configurar um endpoint compatível com OpenAI Chat Completions. A chave do modelo é independente do token de acesso do LÚMEN.

## Persistência

Configure `DATABASE_URL` com PostgreSQL gerenciado para manter conversas, tarefas e memórias após reinicializações e novas implantações. SQLite em disco efêmero não é armazenamento durável em plataformas serverless.
