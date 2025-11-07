# Xiaozhi MCP Bridge

Aplicação ponte que conecta o agente na cloud (xiaozhi.me) ao servidor MCP local (SQL DW), permitindo que o agente chame as ferramentas do MCP local através do WebSocket da xiaozhi.me.

## Arquitetura

```
Agente Cloud (xiaozhi.me)
    ↓ WebSocket (wss://api.xiaozhi.me/mcp/?token=...)
Aplicação Ponte (máquina local)
    ↓ SSH/STDIO
Servidor MCP Local (SQL DW - 10.60.254.6)
```

## Instalação

1. Clone o repositório ou crie o diretório do projeto:
```bash
mkdir xiaozhi-mcp-bridge
cd xiaozhi-mcp-bridge
```

2. Instale as dependências:
```bash
pip install -r requirements.txt
```

3. Configure o arquivo de configuração:
```bash
cp config/config.example.yaml config/config.yaml
# Edite config/config.yaml com suas credenciais
```

4. Configure a senha SSH como variável de ambiente:
```bash
# Windows PowerShell
$env:SSH_PASSWORD = "sua_senha_ssh"

# Windows CMD
set SSH_PASSWORD=sua_senha_ssh

# Linux/macOS
export SSH_PASSWORD="sua_senha_ssh"
```

**OU** configure no arquivo `.env` (copie `.env.example` para `.env` e edite).

## Configuração

Edite o arquivo `config/config.yaml`:

```yaml
xiaozhi:
  websocket_url: "wss://api.xiaozhi.me/mcp/"
  token: "seu_token_aqui"

mcp_local:
  ssh_host: "10.60.254.6"
  ssh_user: "allied"
  ssh_command: "/home/allied/AlliedIT_DW/mcp_server/run_mcp.sh"
  
logging:
  level: "INFO"
  file: "bridge.log"
```

## Uso

### Executar a aplicação

**⚠️ IMPORTANTE:** Para o endpoint aparecer como "Connected" na interface do xiaozhi.me, a aplicação precisa estar rodando continuamente.

```bash
python main.py
```

A aplicação irá:
1. Conectar ao WebSocket da xiaozhi.me
2. Conectar ao servidor MCP local via SSH
3. Fazer proxy das mensagens MCP entre os dois lados

**Para ver instruções detalhadas de execução, consulte [COMO_EXECUTAR.md](COMO_EXECUTAR.md)**

### Executar testes básicos

```bash
python test_basic.py
```

Isso validará os componentes básicos da aplicação sem precisar de conexões reais.

## Como Funciona

A aplicação funciona como uma ponte bidirecional:

1. **Cloud → Local**: Quando o agente na cloud chama uma ferramenta MCP
   - Mensagem chega via WebSocket do xiaozhi.me
   - Bridge extrai o payload JSON-RPC
   - Bridge mapeia o ID da requisição (cloud_id → local_id)
   - Bridge envia para servidor MCP local via SSH/STDIO
   - Bridge aguarda resposta e envia de volta para cloud

2. **Local → Cloud**: Quando servidor MCP local envia notificação
   - Mensagem chega do servidor MCP local
   - Bridge formata como mensagem MCP
   - Bridge envia via WebSocket para cloud

## Troubleshooting

### Erro de conexão SSH
- Verifique se a chave SSH está configurada: `ssh-copy-id allied@10.60.254.6`
- Teste a conexão manualmente: `ssh allied@10.60.254.6 "echo OK"`

### Erro de conexão WebSocket
- Verifique se o token está correto e válido
- Verifique a conectividade com `wss://api.xiaozhi.me/mcp/`

### Logs
Os logs são salvos no arquivo especificado em `config.yaml` (padrão: `bridge.log`)

### Verificar status
A aplicação mostra logs em tempo real no console. Procure por:
- `Conectado ao WebSocket com sucesso` - Conexão cloud estabelecida
- `Conectado ao servidor MCP com sucesso` - Conexão local estabelecida
- `Sessão MCP inicializada com sucesso` - Sessão MCP pronta
- `Proxy Cloud -> Local` - Mensagens sendo encaminhadas

## Estrutura do Projeto

```
xiaozhi-mcp-bridge/
├── src/
│   ├── __init__.py
│   ├── bridge.py              # Classe principal da ponte
│   ├── websocket_client.py    # Cliente WebSocket para xiaozhi.me
│   ├── mcp_client.py          # Cliente MCP local via SSH/STDIO
│   └── message_handler.py     # Handler de mensagens MCP
├── config/
│   └── config.example.yaml    # Arquivo de configuração exemplo
├── requirements.txt
├── README.md
└── main.py                    # Ponto de entrada
```

