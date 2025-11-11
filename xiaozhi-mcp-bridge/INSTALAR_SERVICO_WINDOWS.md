# Instalar Serviço do Windows para Xiaozhi MCP Bridge

Este guia explica como instalar o Xiaozhi MCP Bridge como um serviço do Windows que inicia automaticamente no logon.

## Pré-requisitos

1. **Python instalado** e no PATH do sistema
2. **Privilégios de Administrador**
3. **Dependências instaladas**: `pip install -r requirements.txt`

## Instalação

### 1. Abrir PowerShell como Administrador

- Pressione `Win + X` e selecione "Windows PowerShell (Admin)" ou "Terminal (Admin)"
- Ou clique com botão direito no PowerShell e selecione "Executar como administrador"

### 2. Navegar até o diretório do projeto

```powershell
cd C:\repositorio\xiaozhi\xiaozhi-esp32\xiaozhi-mcp-bridge
```

### 3. Instalar o serviço

```powershell
.\scripts\install_service.ps1
```

O script irá:
- Verificar se o Python está instalado
- Criar o serviço do Windows "XiaozhiMCPBridge"
- Configurar para iniciar automaticamente no logon
- Configurar o diretório de trabalho correto

### 4. Iniciar o serviço

```powershell
.\scripts\start_service.ps1
```

Ou usando o comando nativo:

```powershell
Start-Service -Name XiaozhiMCPBridge
```

## Gerenciar o Serviço

### Verificar Status

```powershell
Get-Service -Name XiaozhiMCPBridge
```

### Iniciar Serviço

```powershell
.\scripts\start_service.ps1
# ou
Start-Service -Name XiaozhiMCPBridge
```

### Parar Serviço

```powershell
.\scripts\stop_service.ps1
# ou
Stop-Service -Name XiaozhiMCPBridge
```

### Reiniciar Serviço

```powershell
Restart-Service -Name XiaozhiMCPBridge
```

### Ver Logs

```powershell
Get-Content bridge.log -Wait -Tail 20
```

## Desinstalar o Serviço

```powershell
.\scripts\uninstall_service.ps1
```

Ou:

```powershell
.\scripts\install_service.ps1 -Uninstall
```

## Gerenciar via Interface Gráfica

1. Abra o **Gerenciador de Serviços**:
   - Pressione `Win + R`
   - Digite `services.msc` e pressione Enter

2. Procure por **"Xiaozhi MCP Bridge"**

3. Clique com botão direito para:
   - Iniciar/Parar/Reiniciar
   - Configurar propriedades
   - Ver logs de eventos

## Configuração do Serviço

O serviço está configurado para:
- **Nome**: `XiaozhiMCPBridge`
- **Display Name**: `Xiaozhi MCP Bridge`
- **Tipo de Inicialização**: Automático (inicia no logon)
- **Conta**: `NT AUTHORITY\LocalService`
- **Diretório de Trabalho**: Diretório onde está o `main.py`

## Solução de Problemas

### Serviço não inicia

1. Verificar se o Python está no PATH do sistema:
   ```powershell
   python --version
   ```

2. Verificar se as dependências estão instaladas:
   ```powershell
   pip install -r requirements.txt
   ```

3. Verificar os logs:
   ```powershell
   Get-Content bridge.log -Tail 50
   ```

4. Verificar eventos do Windows:
   ```powershell
   Get-EventLog -LogName Application -Source "XiaozhiMCPBridge" -Newest 10
   ```

### Serviço para após iniciar

1. Verificar se o arquivo `config/config.yaml` existe e está configurado corretamente
2. Verificar se a variável `SSH_PASSWORD` está configurada (se necessário)
3. Verificar os logs em `bridge.log`

### Permissões

Se o serviço não conseguir acessar arquivos ou rede:
- O serviço roda como `LocalService` por padrão
- Para mais permissões, pode ser necessário alterar a conta do serviço para uma conta de usuário

## Notas Importantes

- O serviço inicia automaticamente quando o Windows faz logon
- Os logs são salvos em `bridge.log` no diretório do projeto
- Para atualizar o código, pare o serviço, faça as alterações e reinicie
- Certifique-se de que o arquivo `.env` (se usado) está acessível pelo serviço

