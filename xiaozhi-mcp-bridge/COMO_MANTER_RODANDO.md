# Como Manter a Bridge Rodando

## Status Atual

A aplicação está configurada e funcionando! Para manter rodando continuamente:

## Opções para Manter Rodando

### Opção 1: Script PowerShell (Recomendado)

```powershell
# Iniciar
.\start_bridge.ps1

# Ver status
.\status_bridge.ps1

# Parar
.\stop_bridge.ps1
```

### Opção 2: Terminal Aberto

Simplesmente deixe o terminal aberto e execute:
```powershell
python main.py
```

### Opção 3: Screen/Tmux (Linux/WSL)

```bash
screen -S xiaozhi-bridge
python main.py
# Desanexar: Ctrl+A depois D
# Reanexar: screen -r xiaozhi-bridge
```

### Opção 4: Serviço Windows (Produção)

Crie um serviço Windows usando NSSM ou Task Scheduler.

## Configurar Variável de Ambiente Permanentemente

### Windows PowerShell (User)
```powershell
[System.Environment]::SetEnvironmentVariable('SSH_PASSWORD', '9jZ4HPyR504FYSt8Xlt5f4', 'User')
```

### Windows PowerShell (System - requer admin)
```powershell
[System.Environment]::SetEnvironmentVariable('SSH_PASSWORD', '9jZ4HPyR504FYSt8Xlt5f4', 'Machine')
```

### Windows CMD
```cmd
setx SSH_PASSWORD "9jZ4HPyR504FYSt8Xlt5f4"
```

**Nota:** Após configurar, reinicie o terminal/PowerShell para a variável ser carregada.

## Verificar se Está Rodando

```powershell
# Ver processos Python
Get-Process python

# Ver logs em tempo real
Get-Content bridge.log -Wait -Tail 20

# Ver últimas linhas
Get-Content bridge.log -Tail 10
```

## Verificar Status na Interface

1. Abra a interface do xiaozhi.me
2. Vá para a página do MCP Endpoint
3. Clique em **"Refresh"**
4. O status deve aparecer como **"Connected"** ✅

## Troubleshooting

### Bridge para de funcionar
- Verifique os logs: `Get-Content bridge.log -Tail 50`
- Reinicie: `.\stop_bridge.ps1` depois `.\start_bridge.ps1`

### WebSocket desconecta frequentemente
- Isso é normal - o servidor pode fechar conexões inativas
- A reconexão automática está funcionando
- O importante é que o MCP está conectado

### SSH não conecta
- Verifique se a variável SSH_PASSWORD está configurada: `echo $env:SSH_PASSWORD`
- Verifique se o Tailscale está conectado: `tailscale status`
- Teste SSH manualmente: `ssh -p 4422 allied@100.124.250.21 "echo OK"`

## Logs

Os logs são salvos em `bridge.log`. Para monitorar em tempo real:

```powershell
Get-Content bridge.log -Wait -Tail 20
```

