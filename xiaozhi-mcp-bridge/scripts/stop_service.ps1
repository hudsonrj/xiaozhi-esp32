# Script para parar o serviço do Windows
# Requer privilégios de Administrador

$ErrorActionPreference = "Stop"

$serviceName = "XiaozhiMCPBridge"

Write-Host "Parando serviço $serviceName..." -ForegroundColor Yellow

try {
    Stop-Service -Name $serviceName -Force
    Start-Sleep -Seconds 2
    
    $service = Get-Service -Name $serviceName
    Write-Host "Serviço parado. Status: $($service.Status)" -ForegroundColor Green
} catch {
    Write-Host "ERRO ao parar serviço: $_" -ForegroundColor Red
    exit 1
}

