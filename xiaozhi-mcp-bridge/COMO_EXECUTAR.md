# Como Executar para Conectar o Endpoint MCP

## Passo a Passo Completo

### 1. Preparar o Ambiente

```bash
# Navegar para o diretório do projeto
cd xiaozhi-mcp-bridge

# Instalar dependências (se ainda não instalou)
pip install -r requirements.txt
```

### 2. Configurar o Arquivo de Configuração

```bash
# Copiar arquivo de exemplo
cp config/config.example.yaml config/config.yaml
```

Edite o arquivo `config/config.yaml` e certifique-se de que o token está correto:

```yaml
xiaozhi:
  websocket_url: "wss://api.xiaozhi.me/mcp/"
  token: "SEU_TOKEN_COMPLETO_AQUI"  # Cole o token completo da URL do endpoint

mcp_local:
  ssh_host: "10.60.254.6"
  ssh_user: "allied"
  ssh_command: "/home/allied/AlliedIT_DW/mcp_server/run_mcp.sh"
  
logging:
  level: "INFO"
  file: "bridge.log"
```

**IMPORTANTE:** Use o token completo da URL do endpoint que aparece na tela do xiaozhi.me.

### 3. Verificar Conexão SSH

Antes de executar, teste se a conexão SSH funciona:

```bash
ssh allied@10.60.254.6 "echo OK"
```

Se pedir senha, configure chave SSH:

```bash
# Gerar chave (se não tiver)
ssh-keygen -t rsa -b 4096

# Copiar para servidor
ssh-copy-id allied@10.60.254.6

# Testar novamente (não deve pedir senha)
ssh allied@10.60.254.6 "echo OK"
```

### 4. Executar a Aplicação Bridge

```bash
python main.py
```

Você deve ver mensagens como:

```
============================================================
Xiaozhi MCP Bridge - Iniciando...
============================================================
2025-01-XX XX:XX:XX - root - INFO - Conectando ao WebSocket: wss://api.xiaozhi.me/mcp/?token=***
2025-01-XX XX:XX:XX - root - INFO - Conectado ao WebSocket com sucesso
2025-01-XX XX:XX:XX - root - INFO - Conectando ao servidor MCP via SSH: allied@10.60.254.6:/home/allied/AlliedIT_DW/mcp_server/run_mcp.sh
2025-01-XX XX:XX:XX - root - INFO - Conectado ao servidor MCP com sucesso
2025-01-XX XX:XX:XX - root - INFO - Sessão MCP inicializada com sucesso
2025-01-XX XX:XX:XX - root - INFO - Bridge iniciada com sucesso
```

### 5. Verificar Status na Interface

1. Abra a interface do xiaozhi.me no navegador
2. Vá para a página do MCP Endpoint
3. Clique no botão **"Refresh"** (Atualizar)
4. O status deve mudar de **"Not Connected"** para **"Connected"** ✅

### 6. Manter a Aplicação Rodando

**IMPORTANTE:** A aplicação precisa estar rodando continuamente para manter a conexão ativa.

- **Para desenvolvimento:** Deixe o terminal aberto e a aplicação rodando
- **Para produção:** Use um gerenciador de processos como `systemd`, `supervisor`, ou `screen`/`tmux`

#### Opção 1: Usar screen (recomendado para testes)

```bash
# Instalar screen (se não tiver)
# Linux: sudo apt-get install screen
# macOS: brew install screen

# Criar sessão screen
screen -S xiaozhi-bridge

# Executar aplicação
python main.py

# Desanexar: Ctrl+A depois D
# Reanexar: screen -r xiaozhi-bridge
```

#### Opção 2: Usar nohup (background)

```bash
nohup python main.py > bridge_output.log 2>&1 &
```

#### Opção 3: Usar systemd (Linux - produção)

Crie `/etc/systemd/system/xiaozhi-bridge.service`:

```ini
[Unit]
Description=Xiaozhi MCP Bridge
After=network.target

[Service]
Type=simple
User=seu_usuario
WorkingDirectory=/caminho/para/xiaozhi-mcp-bridge
ExecStart=/usr/bin/python3 /caminho/para/xiaozhi-mcp-bridge/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Depois:

```bash
sudo systemctl daemon-reload
sudo systemctl enable xiaozhi-bridge
sudo systemctl start xiaozhi-bridge
sudo systemctl status xiaozhi-bridge
```

## Troubleshooting

### Status continua "Not Connected"

1. **Verifique os logs:**
   ```bash
   tail -f bridge.log
   ```

2. **Verifique se a aplicação está rodando:**
   ```bash
   ps aux | grep python
   ```

3. **Verifique conexão WebSocket:**
   - Veja se há erros nos logs sobre conexão WebSocket
   - Verifique se o token está correto e válido

4. **Verifique conexão SSH:**
   - Teste manualmente: `ssh allied@10.60.254.6 "echo OK"`
   - Veja se há erros nos logs sobre conexão SSH

5. **Tente reconectar:**
   - Pare a aplicação (Ctrl+C)
   - Execute novamente: `python main.py`

### Erro de conexão SSH

```bash
# Verificar se SSH está funcionando
ssh -v allied@10.60.254.6 "echo OK"

# Se der erro de host key, adicionar ao known_hosts
ssh-keyscan 10.60.254.6 >> ~/.ssh/known_hosts
```

### Erro de conexão WebSocket

- Verifique se o token está completo (não truncado)
- Verifique se o token não expirou
- Tente copiar o token novamente da interface do xiaozhi.me

### Aplicação para mas conexão continua

A aplicação tem reconexão automática, mas se parar completamente:

1. Verifique os logs para ver o motivo
2. Reinicie a aplicação
3. Para produção, use systemd com `Restart=always`

## Verificação Rápida

Execute este comando para verificar se tudo está configurado:

```bash
# Verificar se arquivo de config existe
test -f config/config.yaml && echo "✓ Config existe" || echo "✗ Config não existe"

# Verificar se token está configurado
grep -q "token:" config/config.yaml && echo "✓ Token configurado" || echo "✗ Token não configurado"

# Verificar conexão SSH
ssh -o ConnectTimeout=5 allied@10.60.254.6 "echo OK" 2>/dev/null && echo "✓ SSH funcionando" || echo "✗ SSH não funciona"

# Verificar dependências Python
python3 -c "import websockets, yaml" 2>/dev/null && echo "✓ Dependências OK" || echo "✗ Dependências faltando"
```

## Próximos Passos

Uma vez conectado:

1. O endpoint aparecerá como **"Connected"** na interface
2. O agente poderá chamar as ferramentas do seu servidor MCP local
3. Você pode testar fazendo perguntas ao agente que usem as ferramentas do SQL DW

