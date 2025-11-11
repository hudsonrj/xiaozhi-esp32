# Script para iniciar o serviço do Windows
# Requer privilégios de Administrador

$ErrorActionPreference = "Stop"

$serviceName = "XiaozhiMCPBridge"

Write-Host "Iniciando serviço $serviceName..." -ForegroundColor Yellow

try {
    Start-Service -Name $serviceName
    Start-Sleep -Seconds 2
    
    $service = Get-Service -Name $serviceName
    if ($service.Status -eq 'Running') {
        Write-Host "Serviço iniciado com sucesso!" -ForegroundColor Green
        Write-Host "Status: $($service.Status)" -ForegroundColor Cyan
    } else {
        Write-Host "Serviço não está rodando. Status: $($service.Status)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "ERRO ao iniciar serviço: $_" -ForegroundColor Red
    exit 1
}

