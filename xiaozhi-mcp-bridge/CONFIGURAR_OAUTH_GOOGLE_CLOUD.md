# Configuração de OAuth 2.0 no Google Cloud Console

## ⚠️ IMPORTANTE: Configurar URIs de Redirecionamento

Para que a autenticação OAuth 2.0 funcione, você precisa configurar os **Authorized redirect URIs** no Google Cloud Console.

## Passo a Passo

### 1. Acessar Google Cloud Console

1. Acesse: https://console.cloud.google.com/
2. Selecione o projeto que contém suas credenciais OAuth 2.0
3. Vá em **APIs & Services** > **Credentials**

### 2. Encontrar suas Credenciais

1. Procure pelo **Client ID**: `581001865946-e0lnpqifbs4i8r82hg37qo4ku86fok66.apps.googleusercontent.com`
2. Clique no nome da credencial para editar

### 3. Configurar URIs de Redirecionamento

Na seção **Authorized redirect URIs**, adicione os seguintes URIs:

```
http://localhost:8080/
http://localhost:8080
http://localhost/
http://localhost
http://127.0.0.1:8080/
http://127.0.0.1:8080
http://127.0.0.1/
http://127.0.0.1
```

**⚠️ IMPORTANTE:** O URI `http://localhost:8080/` (com barra no final) é o mais importante e deve ser adicionado primeiro!

**Como adicionar:**
1. Clique em **+ ADD URI**
2. Cole cada URI acima
3. Clique em **ADD** após cada URI
4. Clique em **SAVE** no final

### 4. Tipo de Aplicação

Certifique-se de que o tipo de aplicação está configurado como:
- **Application type**: `Desktop app` ou `Installed app`

## URIs Necessários

Adicione TODOS estes URIs na lista de **Authorized redirect URIs** (com e sem barra no final):

```
http://localhost:8080/
http://localhost:8080
http://localhost/
http://localhost
http://127.0.0.1:8080/
http://127.0.0.1:8080
http://127.0.0.1/
http://127.0.0.1
```

**⚠️ CRÍTICO:** O URI `http://localhost:8080/` (com barra `/` no final) é o que o `run_local_server` usa por padrão!

## Por que múltiplos URIs?

- `http://localhost` e `http://127.0.0.1` são equivalentes, mas alguns sistemas podem usar um ou outro
- A porta `8080` é a porta padrão usada pelo código, mas o Google OAuth também aceita outras portas
- Ter múltiplos URIs garante compatibilidade em diferentes ambientes

## Verificação

Após configurar:

1. Salve as alterações no Google Cloud Console
2. Aguarde alguns minutos para as mudanças propagarem
3. Execute o servidor novamente
4. A autenticação deve funcionar normalmente

## Erro Comum: "redirect_uri_mismatch"

Se você receber o erro `redirect_uri_mismatch`:

1. Verifique se adicionou TODOS os URIs listados acima
2. Verifique se não há espaços extras ou caracteres especiais
3. Certifique-se de que salvou as alterações no Google Cloud Console
4. Aguarde alguns minutos e tente novamente

## Screenshot de Referência

A seção de configuração deve ficar assim:

```
Authorized redirect URIs
┌─────────────────────────────┐
│ http://localhost:8080/     │  ← MAIS IMPORTANTE (com barra!)
│ http://localhost:8080       │
│ http://localhost/           │
│ http://localhost            │
│ http://127.0.0.1:8080/     │
│ http://127.0.0.1:8080       │
│ http://127.0.0.1/           │
│ http://127.0.0.1            │
└─────────────────────────────┘
```

## Links Úteis

- Google Cloud Console: https://console.cloud.google.com/
- Credenciais OAuth: https://console.cloud.google.com/apis/credentials
- Documentação OAuth 2.0: https://developers.google.com/identity/protocols/oauth2

