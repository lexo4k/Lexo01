# PREÇO ÚNICO — integrações e operação

## Estado implementado em 09/11/2026
- A vitrine pública deixou de carregar os 13 produtos fictícios de demonstração.
- O frontend consulta a API em `https://preco-unico-api.onrender.com`.
- Foi criado um serviço Node.js separado no Render para operações de backend.
- A API possui health/status, leitura de ofertas, redirecionamento rastreado, importação administrativa protegida e registro idempotente de eventos de comissão.
- Foi criado esquema PostgreSQL para ofertas, cliques e comissões.
- Testes automatizados cobrem validação HTTPS, allowlist de links e estados de comissão.
- **Ainda não há banco de dados conectado, parceiro aprovado, feed real, chave administrativa ou comissões reais.** A API retorna catálogo vazio até as dependências serem configuradas. Nenhuma receita foi gerada ou confirmada.

## Cobertura planejada
Categorias preparadas na interface: tecnologia, casa, moda, esportes, mercado, beleza, automotivo, pets e importados. A cobertura depende de feeds e APIs autorizados por cada parceiro.

## Integração de lojas
Cada parceiro precisa de uma integração autorizada própria:
- API oficial, feed de catálogo ou rede de afiliados autorizada;
- aprovação do publisher/afiliado para o tipo de site ou aplicativo;
- identificador de campanha/subID e regras de atribuição;
- limites de uso, atualização, cache, imagens e marcas conforme os termos;
- moeda, país de entrega, preço, frete, estoque, prazo, condição e URL de destino;
- identificação explícita de original, similar, compatível, usado ou recondicionado.

Não fazer scraping proibido, não inventar disponibilidade, não ocultar publicidade afiliada e não comparar produtos diferentes como se fossem o mesmo.

## Receita de afiliados e Mercado Pago
O modelo inicial é afiliado: o consumidor paga diretamente à loja ou ao marketplace. A rede de afiliados ou o anunciante registra a venda, valida a atribuição e paga a comissão conforme contrato e calendário próprios.
- O PREÇO ÚNICO registra cliques e eventos de conversão autorizados, separando comissão estimada, pendente, aprovada e efetivamente paga.
- Clique não é venda e não gera comissão automaticamente.
- Mercado Pago não é automaticamente o processador da compra do consumidor nem o pagador de toda comissão. Só deve ser configurado como destino de recebimento se o programa parceiro oferecer essa modalidade e após confirmação oficial.
- Não criar checkout próprio, split de pagamento ou repasse de dinheiro de clientes na fase inicial de afiliados.
- Uma futura operação de marketplace/checkout próprio exige análise jurídica, fiscal, antifraude, atendimento, logística, reembolsos e contrato com provedor que suporte o modelo.
- Cadastros, contratos e recebimentos devem cumprir os requisitos de idade e representação legal do provedor e do programa. Quando exigido, devem ser administrados por responsável adulto.
- Não solicitar nem armazenar senha, token, código de autenticação, documento ou dado bancário em chat, frontend ou repositório.

## Arquitetura de produção
1. Frontend público: catálogo, busca, filtros e comparação.
2. Backend privado: normalização de catálogo, atualização de ofertas e geração de links autorizados.
3. Banco de dados PostgreSQL: produtos, variantes, lojas, ofertas, atualizações, cliques e eventos de conversão.
4. Painel administrativo com autenticação e permissões.
5. Auditoria: fonte, hora da atualização e histórico de preço.
6. Observabilidade: falhas de API, ofertas expiradas e discrepâncias.
7. Módulo financeiro: conciliação de conversões e comissões; não movimenta fundos de clientes no modelo afiliado.

## Segredos e variáveis
Nunca colocar senhas, cookies, tokens, chaves privadas, documentos ou dados bancários no HTML, JavaScript público, GitHub ou APK. Usar somente variáveis secretas do backend/host, com acesso mínimo e rotação. Não enviar credenciais por chat.
- `DATABASE_URL`: conexão PostgreSQL privada.
- `ADMIN_API_KEY`: segredo de servidor para importação e consulta administrativa.
- `AFFILIATE_ALLOWED_HOSTS`: domínios de rastreamento autorizados, separados por vírgula.
- `FRONTEND_ORIGIN`: origem HTTPS da vitrine.
- Credenciais específicas de parceiros só devem ser criadas depois da aprovação oficial e inseridas no cofre do backend.

Nomes reservados para integrações futuras (não configuradas):
- `AMAZON_ASSOCIATES_TAG`
- `AMAZON_PAAPI_ACCESS_KEY`
- `AMAZON_PAAPI_SECRET_KEY`
- `MERCADO_LIVRE_CLIENT_ID`
- `MERCADO_LIVRE_CLIENT_SECRET`
- `SHOPEE_PARTNER_ID`
- `SHOPEE_PARTNER_KEY`
- `AFFILIATE_WEBHOOK_SECRET`
- `MERCADOPAGO_ACCESS_TOKEN` (somente se uma integração aprovada exigir; nunca no navegador)

## Elegibilidade e rede inicial
A Awin documenta explicitamente feeds de produtos e uso por sites de comparação de preços. Contudo, a documentação de elegibilidade exige que o publisher tenha pelo menos 18 anos. Portanto, qualquer conta, contrato e recebimento da rede precisa ser de um adulto legalmente responsável, sem contornar a regra. Aprovação da rede e de cada anunciante continua necessária.

## Critérios antes do lançamento público
- banco persistente configurado e migrações aplicadas;
- nenhuma oferta fictícia no catálogo de produção;
- feed oficial ativo e autorização do anunciante;
- testes de correspondência de variantes e duplicatas;
- preço e frete com origem e timestamp;
- links de afiliado testados e disclosure visível;
- testes de privacidade, segurança e acessibilidade;
- suporte, política de privacidade, termos e canal de correção de ofertas;
- validação de conversões e pagamentos com cada parceiro.
