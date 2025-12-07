# Integração Google Calendar MCP

Este documento explica como o servidor MCP do Google Calendar foi integrado à bridge.

## Estrutura

- **Servidor MCP Local**: `mcp_google_calendar/server.py`
  - Implementa protocolo JSON-RPC 2.0 via STDIO
  - Fornece 6 ferramentas para gerenciar eventos do Google Calendar
  - Credenciais configuradas via arquivo JSON de service account

- **Bridge Multi-MCP**: `src/bridge_multi.py`
  - Agrega ferramentas de múltiplos servidores MCP
  - Roteia `tools/call` para o servidor correto baseado no nome da ferramenta
  - Intercepta `tools/list` para retornar ferramentas agregadas

## Configuração

O arquivo `config/config.yaml` foi atualizado para incluir o Google Calendar:

```yaml
mcp_servers:
  # Servidor Google Calendar (local)
  - name: "google-calendar"
    local_command: "python mcp_google_calendar/server.py"
    # Credenciais: hudson-3202f-208569b89e03.json (deve estar no diretório raiz)
```

## Credenciais

O arquivo de credenciais `hudson-3202f-208569b89e03.json` deve estar no diretório raiz do projeto (`xiaozhi-mcp-bridge/`).

**IMPORTANTE**: 
- O service account precisa ter acesso aos calendários que você deseja gerenciar
- Para compartilhar um calendário com o service account, vá em Configurações do Google Calendar > Compartilhar com pessoas específicas
- Adicione o email do service account (mcp-google-calendar@hudson-3202f.iam.gserviceaccount.com) com permissões apropriadas

## Dependências

Instale as dependências necessárias:

```bash
pip install -r requirements.txt
```

As dependências do Google Calendar incluem:
- `google-api-python-client>=2.100.0`
- `google-auth-httplib2>=0.1.1`
- `google-auth>=2.23.0`

## Ferramentas Disponíveis

### Google Calendar

1. `google_calendar_list_calendars` - Lista todos os calendários disponíveis
2. `google_calendar_list_events` - Lista eventos do calendário (com filtros opcionais)
3. `google_calendar_get_event` - Obtém detalhes de um evento específico
4. `google_calendar_create_event` - Cria um novo evento no calendário
5. `google_calendar_update_event` - Atualiza um evento existente
6. `google_calendar_delete_event` - Deleta um evento do calendário

## Como Funciona

1. **Inicialização**: A bridge conecta ao servidor Google Calendar via STDIO
2. **Autenticação**: Usa credenciais do arquivo JSON de service account
3. **Listagem de Ferramentas**: Quando o agente solicita `tools/list`, a bridge:
   - Busca ferramentas de todos os servidores MCP (incluindo Google Calendar)
   - Adiciona prefixo `google-calendar_` às ferramentas do Google Calendar
   - Retorna lista agregada de todas as ferramentas
4. **Chamada de Ferramentas**: Quando o agente chama uma ferramenta `google-calendar_*`:
   - A bridge identifica que é do Google Calendar pelo prefixo
   - Remove o prefixo e envia a requisição para o servidor Google Calendar
   - Retorna a resposta para o agente

## Exemplos de Uso

### Listar Calendários
```json
{
  "method": "tools/call",
  "params": {
    "name": "google-calendar_google_calendar_list_calendars",
    "arguments": {}
  }
}
```

### Listar Eventos
```json
{
  "method": "tools/call",
  "params": {
    "name": "google-calendar_google_calendar_list_events",
    "arguments": {
      "time_min": "2024-01-01T00:00:00Z",
      "time_max": "2024-12-31T23:59:59Z",
      "max_results": 10
    }
  }
}
```

### Criar Evento
```json
{
  "method": "tools/call",
  "params": {
    "name": "google-calendar_google_calendar_create_event",
    "arguments": {
      "summary": "Reunião de equipe",
      "description": "Discussão sobre projeto",
      "start_time": "2024-01-15T10:00:00",
      "end_time": "2024-01-15T11:00:00",
      "location": "Sala de reuniões"
    }
  }
}
```

## Formato de Datas

- **Data/Hora**: Formato ISO 8601 (ex: `2024-01-15T10:00:00`)
- **Apenas Data**: Formato ISO 8601 sem hora (ex: `2024-01-15`) - cria evento de dia inteiro
- **Timezone**: Padrão `America/Sao_Paulo` (pode ser ajustado no código)

## Troubleshooting

### Erro: "Arquivo de credenciais não encontrado"
- Verifique se o arquivo `hudson-3202f-208569b89e03.json` está no diretório raiz
- Verifique se o caminho está correto no código

### Erro: "Permission denied" ou "Forbidden"
- Verifique se o service account tem acesso ao calendário
- Compartilhe o calendário com o email do service account

### Erro: "Bibliotecas do Google Calendar não instaladas"
- Execute: `pip install -r requirements.txt`
- Verifique se as bibliotecas foram instaladas corretamente





