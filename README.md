# Android Resource Lab

Aplicativo Android independente para diagnosticar memória, armazenamento e alguns sinais de integridade do dispositivo. Este repositório não está ligado aos projetos Safe Tunnel, FitTrainer ou outros.

## Primeira versão

- Exibe RAM total e disponível informadas pelo Android.
- Exibe capacidade e espaço livre da partição de dados.
- Lista volumes externos que o Android expõe ao aplicativo.
- Verifica alguns indicadores comuns de root em modo somente leitura.
- Mostra fabricante, modelo, versão do Android e versão de build.
- Interface em português, com botão para atualizar os dados.
- Não envia dados do dispositivo para um servidor.

## Limites técnicos

- RAM virtual ou swap usa armazenamento como apoio e não equivale à RAM física.
- Um aplicativo não consegue adicionar chips de RAM ou armazenamento físico.
- O total de armazenamento e o espaço livre são valores diferentes.
- A expansão virtual depende do fabricante e pode não ser exposta por uma API pública.
- A detecção de root é heurística: não encontrar sinais não prova que o aparelho não tem root.
- Esta versão é diagnóstica. Não modifica partições, firmware, jogos ou verificações de segurança e não aplica alterações privilegiadas automaticamente.

## Compilar

Requisitos: JDK 17 e Android SDK com plataforma API 35.

Com Gradle instalado:

    gradle assembleDebug

O APK de depuração fica em:

    app/build/outputs/apk/debug/app-debug.apk

O workflow do GitHub Actions tenta compilar o APK em cada push e disponibilizá-lo como artefato da execução. O artefato de depuração não é uma versão assinada para distribuição na Play Store.

## Próximas etapas

1. Confirmar a compilação em CI.
2. Testar os valores em diferentes fabricantes e versões do Android.
3. Adicionar módulos de otimização somente para operações suportadas, documentadas e reversíveis.
4. Implementar testes para evitar que o app apresente memória virtual como RAM física.
