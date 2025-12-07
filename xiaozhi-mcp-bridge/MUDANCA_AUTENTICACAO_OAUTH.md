# Mudança de Autenticação para OAuth 2.0

## Resumo das Mudanças

A autenticação das APIs do Google foi alterada de **Service Account** para **OAuth 2.0 com credenciais de cliente**. Isso significa que agora será aberta uma janela do navegador para você autorizar o acesso às suas contas do Google.

## O que mudou?

### Antes (Service Account)
- Usava arquivo JSON de service account (`hudson-3202f-208569b89e03.json`)
- Requeria configuração de Domain-Wide Delegation no Google Admin Console
- Funcionava apenas com Google Workspace

### Agora (OAuth 2.0)
- Usa Client ID e Client Secret
- Abre uma janela do navegador para autorização
- Funciona com contas pessoais e Google Workspace
- Mais simples de configurar

## Credenciais Configuradas

As seguintes credenciais já estão configuradas no código:

- **Client ID**: `581001865946-e0lnpqifbs4i8r82hg37qo4ku86fok66.apps.googleusercontent.com`
- **Client Secret**: `SUvj2I3bxbZ-Hjte_OxoAnlO`

Você também pode configurar via variáveis de ambiente:
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`

## Como Funciona

1. **Primeira vez**: Quando você executar o servidor pela primeira vez, será aberta uma janela do navegador
2. **Autorização**: Você precisará fazer login na sua conta do Google e autorizar os escopos solicitados
3. **Token salvo**: O token será salvo em arquivos `.google_calendar_token.json` e `.google_keep_token.json`
4. **Próximas vezes**: O token será reutilizado automaticamente (renovado quando necessário)

## Arquivos Modificados

1. **`google_oauth_helper.py`** (novo): Módulo auxiliar para gerenciar OAuth 2.0
2. **`mcp_google_calendar/server.py`**: Atualizado para usar OAuth 2.0
3. **`mcp_google_keep/server.py`**: Atualizado para usar OAuth 2.0
4. **`requirements.txt`**: Adicionada dependência `google-auth-oauthlib>=1.0.0`
5. **`.gitignore`**: Adicionados arquivos de token para não serem commitados

## ⚠️ CONFIGURAÇÃO NECESSÁRIA NO GOOGLE CLOUD CONSOLE

**IMPORTANTE**: Antes de usar, você precisa configurar os **Authorized redirect URIs** no Google Cloud Console.

Veja o guia completo em: **[CONFIGURAR_OAUTH_GOOGLE_CLOUD.md](CONFIGURAR_OAUTH_GOOGLE_CLOUD.md)**

**Resumo rápido:**
1. Acesse: https://console.cloud.google.com/apis/credentials
2. Encontre seu Client ID: `581001865946-e0lnpqifbs4i8r82hg37qo4ku86fok66.apps.googleusercontent.com`
3. Adicione estes URIs em **Authorized redirect URIs** (⚠️ **IMPORTANTE: com barra no final!**):
   - `http://localhost:8080/` ← **MAIS IMPORTANTE (com barra!)**
   - `http://localhost:8080`
   - `http://localhost/`
   - `http://localhost`
   - `http://127.0.0.1:8080/`
   - `http://127.0.0.1:8080`
   - `http://127.0.0.1/`
   - `http://127.0.0.1`
4. Salve as alterações

## Instalação

Instale a nova dependência:

```bash
pip install google-auth-oauthlib>=1.0.0
```

Ou reinstale todas as dependências:

```bash
pip install -r requirements.txt
```

## Uso

Ao executar os servidores pela primeira vez:

1. O servidor iniciará normalmente
2. Quando uma API do Google for chamada pela primeira vez, será aberta uma janela do navegador
3. Faça login na sua conta do Google
4. Autorize os escopos solicitados:
   - Google Calendar: `https://www.googleapis.com/auth/calendar`
   - Google Keep: `https://www.googleapis.com/auth/keep`
5. Após autorizar, a janela será fechada automaticamente e o token será salvo

## Arquivos de Token

Os tokens são salvos em:
- `.google_calendar_token.json` - Token do Google Calendar
- `.google_keep_token.json` - Token do Google Keep

Estes arquivos são adicionados ao `.gitignore` e não devem ser commitados no repositório.

## Renovação Automática

O sistema renova automaticamente os tokens quando expiram (usando o refresh token). Você só precisará autorizar novamente se:
- O refresh token expirar (geralmente após muito tempo sem uso)
- Você revogar o acesso manualmente no Google Account

## Troubleshooting

### Erro: "Erro ao importar helper de OAuth"
- Verifique se instalou `google-auth-oauthlib`: `pip install google-auth-oauthlib`

### Janela do navegador não abre
- Verifique se há algum firewall bloqueando conexões locais
- Tente executar em um ambiente com interface gráfica

### Token não é salvo
- Verifique permissões de escrita no diretório do projeto
- Verifique se o arquivo `.gitignore` não está bloqueando (os arquivos começam com ponto)

### Erro 403 ou Permission Denied
- Verifique se autorizou todos os escopos solicitados
- Verifique se a API está habilitada no Google Cloud Console:
  - Google Calendar: https://console.cloud.google.com/apis/library/calendar-json.googleapis.com
  - Google Keep: https://console.cloud.google.com/apis/library/keep.googleapis.com

## Vantagens do OAuth 2.0

✅ Funciona com contas pessoais do Google  
✅ Não requer Google Workspace  
✅ Não requer Domain-Wide Delegation  
✅ Mais seguro (você autoriza explicitamente)  
✅ Renovação automática de tokens  
✅ Interface mais amigável (janela do navegador)

