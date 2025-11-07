# Como Configurar o Endpoint MCP na Interface do xiaozhi.me

## Passo a Passo

### 1. Certifique-se que a Bridge está Rodando

A bridge **DEVE estar rodando** para que o endpoint apareça como "Connected" na interface.

```powershell
# Verificar se está rodando
.\status_bridge.ps1

# Se não estiver, iniciar
.\start_bridge.ps1
```

### 2. Na Interface do xiaozhi.me

1. **Vá para a seção "Custom Services"**
   - Na tela de configurações MCP que você mostrou
   - Procure pela seção "Custom Services"
   - Clique no botão **"Get MCP Endpoint"**

2. **O Endpoint já está Configurado**
   - O endpoint MCP já está configurado automaticamente quando você usa o token na URL
   - O token que você tem (`eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9...`) já identifica seu endpoint
   - A bridge envia uma mensagem "hello" com `"features": {"mcp": true}` quando conecta

3. **Verificar Status**
   - Na página do MCP Endpoint (não na tela de configurações)
   - Clique no botão **"Refresh"** ou recarregue a página
   - O status deve aparecer como **"Connected"** se a bridge estiver rodando

### 3. Como Funciona

Quando a bridge conecta ao WebSocket:
1. Envia mensagem "hello" anunciando suporte MCP (`"features": {"mcp": true}`)
2. Recebe resposta "hello" do servidor com `session_id`
3. O xiaozhi.me detecta automaticamente que há um servidor MCP disponível
4. O endpoint aparece na lista como "Connected"

### 4. Verificar Logs

```powershell
# Ver logs em tempo real
Get-Content bridge.log -Wait -Tail 20

# Você deve ver:
# - "Conectado ao WebSocket com sucesso"
# - "Mensagem 'hello' enviada ao servidor"
# - "Recebida mensagem 'hello' do servidor, session_id: ..."
# - "Conectado ao servidor MCP com sucesso"
# - "Sessão MCP inicializada com sucesso"
```

## Importante

- A bridge precisa estar **rodando** para o endpoint aparecer como "Connected"
- O token na URL deve ser o mesmo que você está usando na bridge
- Se o status não mudar para "Connected", verifique:
  - Se a bridge está rodando: `.\status_bridge.ps1`
  - Se há erros nos logs: `Get-Content bridge.log -Tail 50`
  - Se o token está correto na configuração

## Estrutura Esperada

A interface do xiaozhi.me espera que o endpoint MCP:
1. Aceite conexões WebSocket
2. Responda a mensagens JSON-RPC 2.0
3. Implemente os métodos MCP: `initialize`, `tools/list`, `tools/call`

Nossa bridge faz exatamente isso - ela recebe mensagens do xiaozhi.me via WebSocket e as encaminha para o servidor MCP local via SSH.

## Teste

Depois de configurar, teste fazendo uma pergunta ao agente que use as ferramentas do SQL DW, por exemplo:
- "Liste os schemas do DW"
- "Quantos tickets tem a SEPHORA?"
- "Mostre a estrutura da tabela fato_tickets"

