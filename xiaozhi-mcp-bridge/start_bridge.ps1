# Script PowerShell para iniciar a Bridge
# Uso: .\start_bridge.ps1

Write-Host "Iniciando Xiaozhi MCP Bridge..." -ForegroundColor Green

# Verificar se já está rodando
$existing = Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*main.py*" }
if ($existing) {
    Write-Host "Bridge já está rodando (PID: $($existing.Id))" -ForegroundColor Yellow
    exit
}

# Verificar variável de ambiente
if (-not $env:SSH_PASSWORD) {
    Write-Host "AVISO: Variável SSH_PASSWORD não configurada!" -ForegroundColor Yellow
    Write-Host "Configure com: `$env:SSH_PASSWORD = 'sua_senha'" -ForegroundColor Yellow
}

# Iniciar em background
Start-Process python -ArgumentList "main.py" -WindowStyle Hidden

Start-Sleep -Seconds 2

# Verificar se iniciou
$process = Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.StartTime -gt (Get-Date).AddSeconds(-5) }
if ($process) {
    Write-Host "Bridge iniciada com sucesso (PID: $($process.Id))" -ForegroundColor Green
    Write-Host "Logs: bridge.log" -ForegroundColor Cyan
    Write-Host "Para ver logs: Get-Content bridge.log -Wait -Tail 20" -ForegroundColor Cyan
    Write-Host "Para parar: Stop-Process -Id $($process.Id) -Force" -ForegroundColor Cyan
} else {
    Write-Host "Erro ao iniciar bridge. Verifique os logs." -ForegroundColor Red
}

