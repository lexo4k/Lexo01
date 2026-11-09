# PREÇO ÚNICO — integrações e operação

## Estado atual
O site é um protótipo estático. O catálogo contém apenas registros fictícios para demonstrar busca, filtros, categorias e comparação. Nenhuma loja, preço, frete, estoque, API, conta de afiliado ou comissão está conectado.

## Cobertura planejada
Categorias preparadas na interface: tecnologia, casa, moda, esportes, mercado, beleza, automotivo, pets e importados. Novas categorias podem ser adicionadas sem mudar o modelo central.

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
- O PREÇO ÚNICO deve registrar cliques e eventos de conversão autorizados, separando comissão estimada, pendente, aprovada e efetivamente paga.
- Mercado Pago não é automaticamente o processador da compra do consumidor nem o pagador de toda comissão. Só deve ser configurado como destino de recebimento se o programa parceiro oferecer essa modalidade e após confirmação oficial.
- Não criar checkout próprio, split de pagamento ou repasse de dinheiro na fase inicial de afiliados.
- Uma futura operação de marketplace/checkout próprio exige análise jurídica, fiscal, antifraude, atendimento, logística, reembolsos e contrato com provedor que suporte o modelo.
- Qualquer conta comercial, contrato, cadastro financeiro ou recebimento deve cumprir os requisitos de idade e representação legal do provedor e do programa. Quando exigido, deve ser administrado por responsável adulto.
- Não solicitar nem armazenar senha, token, código de autenticação, documento ou dado bancário em chat, frontend ou repositório.

## Arquitetura de produção
1. Frontend público: catálogo, busca, filtros e comparação.
2. Backend privado: normalização de catálogo, atualização de ofertas e geração de links autorizados.
3. Banco de dados: produtos, variantes, lojas, ofertas, atualizações, cliques e eventos de conversão.
4. Painel administrativo com autenticação e permissões.
5. Auditoria: fonte, hora da atualização e histórico de preço.
6. Observabilidade: falhas de API, ofertas expiradas e discrepâncias.
7. Módulo financeiro: conciliação de conversões e comissões; não movimenta fundos de clientes no modelo afiliado.

## Segredos e contas
Nunca colocar senhas, cookies, tokens, chaves privadas, documentos ou dados bancários no HTML, JavaScript público, GitHub ou APK. Usar apenas variáveis secretas do backend/host, com acesso mínimo e rotação. Não enviar credenciais por chat. Não reutilizar senhas entre serviços.

Nomes de variáveis reservadas para configuração futura (sem valores):
- AMAZON_ASSOCIATES_TAG
- AMAZON_PAAPI_ACCESS_KEY
- AMAZON_PAAPI_SECRET_KEY
- MERCADO_LIVRE_CLIENT_ID
- MERCADO_LIVRE_CLIENT_SECRET
- SHOPEE_PARTNER_ID
- SHOPEE_PARTNER_KEY
- AFFILIATE_WEBHOOK_SECRET
- MERCADOPAGO_ACCESS_TOKEN (somente se houver uma integração própria aprovada e necessária no backend; nunca no navegador)

Esses nomes não significam que as APIs estão aprovadas ou conectadas. Credenciais só devem ser criadas depois da aprovação oficial e inseridas no cofre de segredos do backend.

## Regras de elegibilidade
Cada programa define países aceitos, idade/representação legal, tráfego permitido, tipo de publisher, comissões, atribuição, pagamento e impostos. Não existe cadastro universal nem aprovação automática. Quando a plataforma exigir maioridade ou representação empresarial, a conta deve ser aberta e administrada por adulto legalmente responsável, seguindo os termos.

## Critérios antes do lançamento público
- nenhuma oferta fictícia no catálogo de produção;
- testes de correspondência de variantes e duplicatas;
- preço e frete com origem e timestamp;
- links de afiliado testados e disclosure visível;
- testes de privacidade, segurança e acessibilidade;
- suporte, política de privacidade, termos e canal de correção de ofertas;
- validação de conversões e pagamentos com cada parceiro.
