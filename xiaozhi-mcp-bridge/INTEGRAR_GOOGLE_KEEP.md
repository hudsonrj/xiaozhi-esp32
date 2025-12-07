# Integração Google Keep MCP

Este documento explica como o servidor MCP do Google Keep foi integrado à bridge usando a **API oficial do Google Keep**.

## API Oficial do Google Keep

A implementação usa a **API oficial do Google Keep** (`keep.googleapis.com`) com:
- **Service Account**: Usa o mesmo arquivo `hudson-3202f-208569b89e03.json` do Google Calendar
- **Escopo**: `https://www.googleapis.com/auth/keep`
- **Documentação**: https://developers.google.com/workspace/keep?hl=pt_BR

## ⚠️ IMPORTANTE: Autenticação e Autorização

A API oficial do Google Keep requer configuração específica:

### Para Service Accounts (Google Workspace)

Se você está usando um **service account** (como `hudson-3202f-208569b89e03.json`), é necessário:

1. **Habilitar a API do Google Keep** no Google Cloud Console
2. **Configurar delegação em todo o domínio** (Domain-Wide Delegation)
   - Acesse: Google Admin Console > Segurança > Controle de acesso à API
   - Adicione o Client ID do service account
   - Autorize os escopos: `https://www.googleapis.com/auth/keep`
3. **A API está disponível apenas para Google Workspace** (não funciona com contas pessoais)

### Para Contas Pessoais

Para contas pessoais do Google, a API pode ter limitações. Considere usar OAuth2 com credenciais de usuário.

**Documentação oficial de troubleshooting:**
https://developers.google.com/workspace/keep/api/troubleshoot-authentication-authorization?hl=pt-br

## Estrutura

- **Servidor MCP Local**: `mcp_google_keep/server.py`
  - Implementa protocolo JSON-RPC 2.0 via STDIO
  - Fornece 7 ferramentas para gerenciar notas do Google Keep
  - Requer credenciais OAuth2 de usuário (email/senha)

- **Bridge Multi-MCP**: `src/bridge_multi.py`
  - Agrega ferramentas de múltiplos servidores MCP
  - Roteia `tools/call` para o servidor correto baseado no nome da ferramenta
  - Intercepta `tools/list` para retornar ferramentas agregadas

## Configuração

### 1. Instalar Dependências

```bash
pip install -r requirements.txt
```

A dependência `gkeepapi>=0.14.0` será instalada automaticamente.

### 2. Configurar Credenciais

**IMPORTANTE**: Você precisa configurar as variáveis de ambiente `KEEP_EMAIL` e `KEEP_PASSWORD`:

**Windows (PowerShell):**
```powershell
$env:KEEP_EMAIL = "seu-email@gmail.com"
$env:KEEP_PASSWORD = "sua-senha-aqui"
```

**Windows (CMD):**
```cmd
set KEEP_EMAIL=seu-email@gmail.com
set KEEP_PASSWORD=sua-senha-aqui
```

**Linux/Mac:**
```bash
export KEEP_EMAIL="seu-email@gmail.com"
export KEEP_PASSWORD="sua-senha-aqui"
```

**Ou criar arquivo `.env` no diretório raiz:**
```env
KEEP_EMAIL=seu-email@gmail.com
KEEP_PASSWORD=sua-senha-aqui
```

### 3. Configurar no config.yaml

O arquivo `config/config.yaml` já foi atualizado para incluir o Google Keep:

```yaml
mcp_servers:
  # Servidor Google Keep (local)
  - name: "google-keep"
    local_command: "python mcp_google_keep/server.py"
    # Credenciais: Configure KEEP_EMAIL e KEEP_PASSWORD como variáveis de ambiente
    # NOTA: Google Keep não funciona com service accounts - requer credenciais OAuth2 de usuário
```

## Autenticação

O servidor tentará autenticar usando:
1. **Variáveis de ambiente** `KEEP_EMAIL` e `KEEP_PASSWORD` (prioridade)
2. **Token salvo** em `.keep_token` (se existir e email configurado)
3. **Erro** se nenhuma credencial estiver disponível

Após a primeira autenticação bem-sucedida, um token será salvo em `.keep_token` para reutilização futura.

## Ferramentas Disponíveis

### Google Keep (11 ferramentas)

**Gerenciamento de Notas:**
1. `google_keep_list_notes` - Lista notas com filtros e paginação
2. `google_keep_get_note` - Obtém detalhes completos de uma nota (incluindo anexos)
3. `google_keep_create_text_note` - Cria uma nota de texto
4. `google_keep_create_list_note` - Cria uma nota de lista com itens marcáveis
5. `google_keep_create_note` - Cria nota genérica (método flexível)
6. `google_keep_update_note` - Atualiza uma nota existente
7. `google_keep_delete_note` - Deleta uma nota

**Permissões:**
8. `google_keep_get_permissions` - Lista permissões de uma nota
9. `google_keep_create_permission` - Compartilha nota com usuário (READER/WRITER)
10. `google_keep_delete_permission` - Remove compartilhamento

**Anexos:**
11. `google_keep_get_attachments` - Lista anexos de uma nota
12. `google_keep_download_attachment` - Baixa um anexo de uma nota

## Como Funciona

1. **Inicialização**: A bridge conecta ao servidor Google Keep via STDIO
2. **Autenticação**: Usa credenciais OAuth2 de usuário (email/senha)
3. **Listagem de Ferramentas**: Quando o agente solicita `tools/list`, a bridge:
   - Busca ferramentas de todos os servidores MCP (incluindo Google Keep)
   - Adiciona prefixo `google-keep_` às ferramentas do Google Keep
   - Retorna lista agregada de todas as ferramentas
4. **Chamada de Ferramentas**: Quando o agente chama uma ferramenta `google-keep_*`:
   - A bridge identifica que é do Google Keep pelo prefixo
   - Remove o prefixo e envia a requisição para o servidor Google Keep
   - Retorna a resposta para o agente

## Exemplos de Uso

### Listar Notas
```json
{
  "method": "tools/call",
  "params": {
    "name": "google-keep_google_keep_list_notes",
    "arguments": {
      "pinned": true
    }
  }
}
```

### Criar Nota de Texto
```json
{
  "method": "tools/call",
  "params": {
    "name": "google-keep_google_keep_create_text_note",
    "arguments": {
      "title": "Lembrete importante",
      "text_content": "Não esquecer de fazer isso"
    }
  }
}
```

### Criar Nota de Lista
```json
{
  "method": "tools/call",
  "params": {
    "name": "google-keep_google_keep_create_list_note",
    "arguments": {
      "title": "Tarefas do dia",
      "list_items": [
        {
          "text": "Enviar convites da reunião",
          "checked": true
        },
        {
          "text": "Preparar apresentação",
          "checked": false,
          "child_list_items": [
            {"text": "Revisar métricas"},
            {"text": "Analisar projeções de vendas"}
          ]
        }
      ]
    }
  }
}
```

### Listar Notas com Filtros
```json
{
  "method": "tools/call",
  "params": {
    "name": "google-keep_google_keep_list_notes",
    "arguments": {
      "filter": "create_time > \"2024-01-01T00:00:00Z\" -trashed",
      "page_size": 10
    }
  }
}
```

### Baixar Anexo
```json
{
  "method": "tools/call",
  "params": {
    "name": "google-keep_google_keep_get_attachments",
    "arguments": {
      "note_id": "notes/ABC123"
    }
  }
}
// Depois usar o attachment_name retornado:
{
  "method": "tools/call",
  "params": {
    "name": "google-keep_google_keep_download_attachment",
    "arguments": {
      "attachment_name": "notes/ABC123/attachments/XYZ789",
      "mime_type": "image/png",
      "output_path": "anexo.png"
    }
  }
}
```

### Buscar Notas
```json
{
  "method": "tools/call",
  "params": {
    "name": "google-keep_google_keep_search_notes",
    "arguments": {
      "query": "reunião"
    }
  }
}
```

## Cores Disponíveis

As cores disponíveis para notas são:
- `DEFAULT`, `RED`, `ORANGE`, `YELLOW`, `GREEN`, `TEAL`, `BLUE`, `DARKBLUE`, `PURPLE`, `PINK`, `BROWN`, `GRAY`

## Troubleshooting

### Erro: "Arquivo de credenciais não encontrado"
- Verifique se o arquivo `hudson-3202f-208569b89e03.json` está no diretório raiz
- Verifique se o caminho está correto no código

### Erro: "Erro ao criar serviço Google Keep"
- **Verifique se a API do Google Keep está habilitada** no Google Cloud Console:
  1. Acesse: https://console.cloud.google.com/apis/library
  2. Procure por "Google Keep API"
  3. Clique em "Ativar"
- Verifique se o projeto está correto no arquivo de credenciais

### Erro: "Permission denied" ou "Forbidden" (403)
- **Para Service Accounts**: Configure delegação em todo o domínio:
  1. Acesse: Google Admin Console > Segurança > Controle de acesso à API
  2. Adicione o Client ID do service account (encontrado no arquivo JSON)
  3. Autorize o escopo: `https://www.googleapis.com/auth/keep`
- **Para OAuth2**: Verifique se o usuário concedeu as permissões necessárias

### Erro: "API não disponível para este tipo de conta"
- A API oficial do Google Keep está disponível principalmente para **Google Workspace**
- Contas pessoais do Google podem ter limitações
- Verifique se você está usando uma conta do Google Workspace

### Erro: "Invalid scope" ou "Scope not authorized"
- Verifique se o escopo `https://www.googleapis.com/auth/keep` está autorizado
- Para service accounts, configure a delegação em todo o domínio no Admin Console
- Para OAuth2, verifique se o escopo foi solicitado corretamente

### Erro: "Service account não funciona"
- **Para Google Workspace**: Service accounts funcionam com delegação em todo o domínio
- **Para contas pessoais**: Use OAuth2 com credenciais de usuário
- Consulte: https://developers.google.com/workspace/keep/api/troubleshoot-authentication-authorization?hl=pt-br

### Erro: "Bibliotecas do Google não instaladas"
- Execute: `pip install -r requirements.txt`
- Verifique se as bibliotecas foram instaladas corretamente:
  - `google-api-python-client>=2.100.0`
  - `google-auth-httplib2>=0.1.1`
  - `google-auth>=2.23.0`
  - `requests>=2.31.0`

## Segurança

⚠️ **ATENÇÃO**: 
- As credenciais de usuário são armazenadas em variáveis de ambiente
- O token de autenticação é salvo em `.keep_token` (não commitar no git!)
- Use senhas de app se tiver 2FA habilitado
- Considere usar uma conta específica para automação

## Diferenças do Google Calendar

| Aspecto | Google Calendar | Google Keep |
|---------|----------------|-------------|
| API Oficial | ✅ Sim | ✅ Sim (Google Workspace) |
| Service Account | ✅ Funciona | ✅ Funciona (com delegação em todo o domínio) |
| OAuth2 Usuário | ✅ Funciona | ✅ Funciona |
| Google Workspace | ✅ Funciona | ✅ Requerido para service accounts |
| Contas Pessoais | ✅ Funciona | ⚠️ Limitações |
| Credenciais Necessárias | JSON de service account | JSON de service account (Workspace) ou OAuth2 |

## Links Úteis

- **Documentação Oficial**: https://developers.google.com/workspace/keep?hl=pt_BR
- **Troubleshooting Autenticação**: https://developers.google.com/workspace/keep/api/troubleshoot-authentication-authorization?hl=pt-br
- **Guia de Autenticação**: https://developers.google.com/workspace/keep/api/guides?hl=pt-BR

