# Script para verificar status e informações do serviço

$serviceName = "XiaozhiMCPBridge"

Write-Host "`n=== Status do Serviço: $serviceName ===" -ForegroundColor Green

$service = Get-Service -Name $serviceName -ErrorAction SilentlyContinue

if (-not $service) {
    Write-Host "Serviço não está instalado." -ForegroundColor Yellow
    Write-Host "Para instalar, execute: .\scripts\install_service.ps1" -ForegroundColor Cyan
    exit 0
}

Write-Host "`nNome: $($service.Name)" -ForegroundColor Cyan
Write-Host "Display Name: $($service.DisplayName)" -ForegroundColor Cyan
Write-Host "Status: $($service.Status)" -ForegroundColor $(if ($service.Status -eq 'Running') { 'Green' } else { 'Yellow' })
Write-Host "Tipo de Inicialização: $($service.StartType)" -ForegroundColor Cyan

# Verificar configuração do serviço
$serviceConfig = Get-WmiObject Win32_Service -Filter "Name='$serviceName'"
if ($serviceConfig) {
    Write-Host "`nConfiguração:" -ForegroundColor Yellow
    Write-Host "  Executável: $($serviceConfig.PathName)" -ForegroundColor Gray
    Write-Host "  Conta: $($serviceConfig.StartName)" -ForegroundColor Gray
    Write-Host "  Diretório: $($serviceConfig.PathName)" -ForegroundColor Gray
}

# Verificar se o processo está rodando
if ($service.Status -eq 'Running') {
    $process = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -like "*main.py*"
    }
    if ($process) {
        Write-Host "`nProcesso Python rodando:" -ForegroundColor Green
        Write-Host "  PID: $($process.Id)" -ForegroundColor Gray
        Write-Host "  Memória: $([math]::Round($process.WorkingSet64 / 1MB, 2)) MB" -ForegroundColor Gray
    }
}

# Verificar logs recentes
$logFile = Join-Path (Split-Path -Parent $PSScriptRoot) "bridge.log"
if (Test-Path $logFile) {
    Write-Host "`nÚltimas linhas do log:" -ForegroundColor Yellow
    Get-Content $logFile -Tail 5 | ForEach-Object {
        Write-Host "  $_" -ForegroundColor Gray
    }
} else {
    Write-Host "`nArquivo de log não encontrado: $logFile" -ForegroundColor Yellow
}

Write-Host "`nComandos úteis:" -ForegroundColor Yellow
Write-Host "  Iniciar: Start-Service -Name $serviceName" -ForegroundColor White
Write-Host "  Parar: Stop-Service -Name $serviceName" -ForegroundColor White
Write-Host "  Reiniciar: Restart-Service -Name $serviceName" -ForegroundColor White
Write-Host "  Ver logs: Get-Content bridge.log -Wait -Tail 20" -ForegroundColor White

