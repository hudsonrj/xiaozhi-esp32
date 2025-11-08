# Integração Portal da Transparência

Este documento explica como o servidor MCP do Portal da Transparência foi integrado à bridge.

## Estrutura

- **Servidor MCP Local**: `mcp_portal_transparencia/server.js`
  - Implementa protocolo JSON-RPC 2.0 via STDIO
  - Fornece 7 ferramentas para consultar dados do Portal da Transparência
  - API Key configurada via variável de ambiente `PORTAL_API_KEY`

- **Bridge Multi-MCP**: `src/bridge_multi.py`
  - Agrega ferramentas de múltiplos servidores MCP
  - Roteia `tools/call` para o servidor correto baseado no nome da ferramenta
  - Intercepta `tools/list` para retornar ferramentas agregadas

## Configuração

O arquivo `config/config.yaml` foi atualizado para suportar múltiplos servidores:

```yaml
mcp_servers:
  # Servidor SQL DW (remoto via SSH)
  - name: "sql-dw"
    ssh_host: "100.124.250.21"
    ssh_user: "allied"
    ssh_port: 4422
    ssh_command: "/home/allied/AlliedIT_DW/mcp_server/run_mcp.sh"
  
  # Servidor Portal da Transparência (local)
  - name: "portal-transparencia"
    local_command: "node mcp_portal_transparencia/server.js"
```

## Ferramentas Disponíveis

### Portal da Transparência

1. `portal_check_api_key` - Verifica se a API key está configurada
2. `portal_servidores_consultar` - Consulta servidores públicos
3. `portal_viagens_consultar` - Consulta viagens a serviço
4. `portal_contratos_consultar` - Consulta contratos públicos
5. `portal_despesas_consultar` - Consulta despesas públicas
6. `portal_beneficios_consultar` - Consulta programas sociais
7. `portal_licitacoes_consultar` - Consulta processos licitatórios

### SQL DW (SENSR)

- `list_tables` - Lista tabelas
- `execute_select` - Executa consultas SQL
- `count_records` - Conta registros
- `get_table_sample` - Obtém amostra de dados
- `describe_table` - Descreve estrutura da tabela
- E outras ferramentas do sistema SENSR

## Como Funciona

1. **Inicialização**: A bridge conecta a ambos os servidores MCP
2. **tools/list**: Quando o agente solicita a lista de ferramentas:
   - A bridge intercepta a requisição
   - Busca ferramentas de todos os servidores conectados
   - Agrega e retorna todas as ferramentas em uma única resposta
3. **tools/call**: Quando o agente chama uma ferramenta:
   - A bridge identifica qual servidor deve processar (baseado no prefixo do nome)
   - Roteia a chamada para o servidor correto
   - Retorna a resposta ao agente

## Execução

```powershell
# Configurar senha SSH (se necessário)
$env:SSH_PASSWORD = "sua_senha"

# Configurar API Key do Portal (opcional, usa padrão se não configurado)
$env:PORTAL_API_KEY = "sua_api_key"

# Iniciar bridge
.\start_bridge.ps1
```

## Verificação

Após iniciar a bridge, verifique os logs:

```powershell
.\monitor_logs.ps1
```

Você deve ver mensagens como:
- "Conectando ao servidor MCP: sql-dw"
- "Conectando ao servidor MCP: portal-transparencia"
- "Total de ferramentas agregadas: X"

No agente xiaozhi.me, todas as ferramentas de ambos os servidores devem aparecer disponíveis.

