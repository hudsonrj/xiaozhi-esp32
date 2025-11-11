# Script para desinstalar o serviço do Windows
# Requer privilégios de Administrador

$ErrorActionPreference = "Stop"

# Verificar se está rodando como Administrador
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERRO: Este script requer privilégios de Administrador!" -ForegroundColor Red
    Write-Host "Execute: Start-Process powershell -Verb RunAs -ArgumentList '-File $PSCommandPath'" -ForegroundColor Yellow
    exit 1
}

$serviceName = "XiaozhiMCPBridge"

Write-Host "`n=== Desinstalando Serviço: $serviceName ===" -ForegroundColor Yellow

$service = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
if (-not $service) {
    Write-Host "Serviço não encontrado." -ForegroundColor Yellow
    exit 0
}

if ($service.Status -eq 'Running') {
    Write-Host "Parando serviço..." -ForegroundColor Yellow
    Stop-Service -Name $serviceName -Force
    Start-Sleep -Seconds 2
}

Write-Host "Removendo serviço..." -ForegroundColor Yellow
sc.exe delete $serviceName

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nServiço desinstalado com sucesso!" -ForegroundColor Green
} else {
    Write-Host "`nERRO ao desinstalar serviço." -ForegroundColor Red
    exit 1
}

