# Verificação de SSH

## Problema Atual
O SSH está retornando "Connection refused" quando executado pelo Python.

## Verificações Necessárias

### 1. Testar SSH Manualmente
Execute no PowerShell/CMD:
```bash
ssh allied@100.124.250.21 "echo OK"
```

Se funcionar manualmente mas não pelo Python, pode ser:
- Problema de permissões
- Problema com o caminho do SSH no Windows
- Necessidade de configuração adicional

### 2. Verificar Tailscale
```bash
tailscale status
```

Certifique-se de que está conectado e o IP 100.124.250.21 está visível.

### 3. Verificar Porta SSH
Se o SSH usa uma porta diferente de 22, precisamos atualizar a configuração.

### 4. Testar com Porta Específica
```bash
ssh -p PORTA allied@100.124.250.21 "echo OK"
```

## Solução Alternativa

Se o SSH não funcionar pelo Python no Windows, podemos:
1. Usar uma abordagem diferente (paramiko, etc.)
2. Executar em WSL (Windows Subsystem for Linux)
3. Usar um túnel/proxy diferente

## Próximos Passos

Por favor, execute manualmente:
```bash
ssh allied@100.124.250.21 "echo OK"
```

E informe:
1. Funciona? (sim/não)
2. Qual porta SSH está usando? (padrão é 22)
3. Precisa de autenticação especial? (chave, senha, etc.)

