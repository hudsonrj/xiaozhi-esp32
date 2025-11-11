# Script PowerShell para iniciar a Bridge
# Uso: .\start_bridge.ps1

Write-Host "Iniciando Xiaozhi MCP Bridge..." -ForegroundColor Green

# Verificar se já está rodando
$existing = Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*main.py*" }
if ($existing) {
    Write-Host "Bridge já está rodando (PID: $($existing.Id))" -ForegroundColor Yellow
    exit
}

# Verificar variável de ambiente ou arquivo .env
$sshPasswordSet = $false
if ($env:SSH_PASSWORD) {
    $sshPasswordSet = $true
} elseif (Test-Path ".env") {
    $envContent = Get-Content ".env" -Raw
    if ($envContent -match "SSH_PASSWORD\s*=\s*(.+)") {
        $sshPasswordSet = $true
    }
}

if (-not $sshPasswordSet) {
    Write-Host "AVISO: SSH_PASSWORD não configurada (nem em variável de ambiente nem em .env)!" -ForegroundColor Yellow
    Write-Host "Configure em .env ou com: `$env:SSH_PASSWORD = 'sua_senha'" -ForegroundColor Yellow
} else {
    Write-Host "SSH_PASSWORD configurada (carregada do .env ou variável de ambiente)" -ForegroundColor Green
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

