# MemDroid (protótipo Android sem root)

Este projeto demonstra busca, refinamento e alteração de valores numéricos **dentro do próprio processo do MemDroid**. Não acessa a memória de outros aplicativos nem contorna as proteções do Android.

## Compilar e instalar

Requisitos: JDK 17 e Android SDK Platform 35. Abra a pasta `MemDroid` no Android Studio, sincronize o Gradle e execute o módulo `app`.

O GitHub Actions compila o APK de depuração automaticamente quando os arquivos deste projeto mudam. O APK fica disponível em **Actions → MemDroid Android build → Artifacts**.

## Como testar

1. Toque em **Carregar laboratório** para carregar valores de demonstração.
2. Digite um número inteiro e toque em **Buscar valor**.
3. Digite outro valor existente e toque em **Refinar busca** para filtrar os resultados atuais.
4. Digite um novo número e toque em **Aplicar novo valor aos resultados** para editar os resultados encontrados.
5. Toque em **Restaurar laboratório** para reiniciar os valores.

## Limitações importantes

- Os valores e IDs são dados de demonstração mantidos dentro do próprio app, não endereços reais de memória.
- Não edita jogos ou aplicativos de terceiros.
- `android:debuggable=true` não concede automaticamente permissão para ler a memória de outro processo.
- A edição de memória entre processos depende das permissões e APIs autorizadas pelo Android; não é prometida em aparelhos sem root.

## Compilação automatizada

O workflow `.github/workflows/memdroid-build.yml` usa JDK 17, Android SDK Platform 35 e Gradle 8.7. Após um push que altere arquivos em `MemDroid/`, o GitHub Actions compila `app-debug.apk` e publica o arquivo como artefato por 14 dias. O APK de depuração não é uma versão assinada para distribuição na Play Store.
