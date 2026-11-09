# PREÇO ÚNICO API

Backend inicial para catálogo real, links de afiliados, rastreamento de cliques e conciliação de comissões.

## Estado
- API de saúde e estado do catálogo.
- Importação administrativa protegida por chave de servidor.
- Validação HTTPS e lista de domínios autorizados para links de afiliado.
- Registro de cliques e redirecionamento somente para ofertas ativas.
- Registro idempotente de eventos de comissão, sem confundir clique com venda.
- Banco PostgreSQL; não há produtos fictícios nem geração de comissão simulada.

## Executar
Node.js 22+.

```sh
npm install
npm test
npm start
```

## Banco
Configure `DATABASE_URL` no ambiente privado do serviço e execute `schema.sql` uma vez no banco. Sem banco, a API permanece saudável, mas não publica ofertas e não registra cliques.

## Variáveis de ambiente
- `DATABASE_URL`: conexão PostgreSQL privada.
- `ADMIN_API_KEY`: segredo longo para operações administrativas; nunca no navegador.
- `AFFILIATE_ALLOWED_HOSTS`: domínios de rastreamento autorizados, separados por vírgula.
- `FRONTEND_ORIGIN`: origem HTTPS do site público.
- `PORT`: fornecida pelo host.

Nenhuma credencial real é incluída no repositório. Integrações de parceiros só podem ser ativadas após aprovação, documentação oficial e credenciais legítimas fornecidas pelo responsável autorizado.
