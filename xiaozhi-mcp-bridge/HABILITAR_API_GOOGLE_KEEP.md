# Como Habilitar a API do Google Keep

## ⚠️ Erro: invalid_scope

Se você está recebendo o erro `Erro 400: invalid_scope` com a mensagem "Some requested scopes cannot be shown: [https://www.googleapis.com/auth/keep]", isso significa que a **API do Google Keep não está habilitada** no seu projeto do Google Cloud Console.

## Passo a Passo para Habilitar

### 1. Acessar Google Cloud Console

1. Acesse: https://console.cloud.google.com/
2. Selecione o projeto: **project-581001865946** (ou o projeto que contém suas credenciais OAuth)

### 2. Habilitar a API do Google Keep

1. Vá em **APIs & Services** > **Library** (Biblioteca)
2. Na busca, digite: **Google Keep API**
3. Clique no resultado: **Google Keep API**
4. Clique no botão **ENABLE** (Habilitar)
5. Aguarde alguns segundos para a API ser habilitada

**Link direto:** https://console.cloud.google.com/apis/library/keep.googleapis.com

### 3. Verificar se está Habilitada

1. Vá em **APIs & Services** > **Enabled APIs** (APIs Habilitadas)
2. Procure por **Google Keep API**
3. Se aparecer na lista, está habilitada ✅

### 4. Verificar Escopos OAuth

1. Vá em **APIs & Services** > **OAuth consent screen** (Tela de consentimento OAuth)
2. Verifique se o escopo `https://www.googleapis.com/auth/keep` está listado
3. Se não estiver, você pode precisar adicionar manualmente ou ele será adicionado automaticamente após habilitar a API

## ⚠️ IMPORTANTE: Limitações da API do Google Keep

A API do Google Keep tem algumas limitações:

1. **Disponibilidade**: A API pode estar disponível apenas para:
   - Contas do Google Workspace (não contas pessoais)
   - Projetos específicos aprovados pelo Google

2. **Escopo**: O escopo `https://www.googleapis.com/auth/keep` pode não estar disponível para todos os tipos de aplicação OAuth

3. **Documentação Oficial**: 
   - https://developers.google.com/workspace/keep?hl=pt_BR
   - https://developers.google.com/workspace/keep/api/troubleshoot-authentication-authorization?hl=pt-br

## Alternativas se a API não Estiver Disponível

Se mesmo após habilitar a API você ainda receber o erro `invalid_scope`, pode ser que:

1. **A API não esteja disponível para contas pessoais** - apenas Google Workspace
2. **O projeto precisa de aprovação** do Google
3. **A API pode ter sido descontinuada** ou restringida

Nesse caso, você pode considerar:
- Usar apenas Google Calendar (que funciona normalmente)
- Verificar se há uma API alternativa para gerenciar notas
- Contatar o suporte do Google para solicitar acesso

## Verificação Rápida

Execute este comando para verificar se a API está habilitada:

```bash
# No Google Cloud Console, vá em:
# APIs & Services > Enabled APIs
# E procure por "Google Keep API"
```

Ou acesse diretamente:
https://console.cloud.google.com/apis/library/keep.googleapis.com

Se aparecer o botão "ENABLE", clique nele. Se aparecer "MANAGE", a API já está habilitada.


