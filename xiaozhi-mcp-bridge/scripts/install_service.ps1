# Script para instalar o serviço do Windows para o Xiaozhi MCP Bridge
# Requer privilégios de Administrador

param(
    [switch]$Uninstall
)

$ErrorActionPreference = "Stop"

# Verificar se está rodando como Administrador
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERRO: Este script requer privilégios de Administrador!" -ForegroundColor Red
    Write-Host "Execute: Start-Process powershell -Verb RunAs -ArgumentList '-File $PSCommandPath'" -ForegroundColor Yellow
    exit 1
}

$serviceName = "XiaozhiMCPBridge"
$scriptDir = Split-Path -Parent $PSScriptRoot
$pythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source

if (-not $pythonExe) {
    Write-Host "ERRO: Python não encontrado no PATH!" -ForegroundColor Red
    Write-Host "Certifique-se de que o Python está instalado e no PATH do sistema." -ForegroundColor Yellow
    exit 1
}

Write-Host "Python encontrado: $pythonExe" -ForegroundColor Green

if ($Uninstall) {
    Write-Host "`nDesinstalando serviço $serviceName..." -ForegroundColor Yellow
    
    $service = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
    if ($service) {
        if ($service.Status -eq 'Running') {
            Stop-Service -Name $serviceName -Force
            Write-Host "Serviço parado." -ForegroundColor Green
        }
        sc.exe delete $serviceName
        Write-Host "Serviço desinstalado com sucesso!" -ForegroundColor Green
    } else {
        Write-Host "Serviço não encontrado." -ForegroundColor Yellow
    }
    exit 0
}

Write-Host "`n=== Instalando Serviço do Windows: $serviceName ===" -ForegroundColor Green

# Verificar se o serviço já existe
$existingService = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
if ($existingService) {
    Write-Host "Serviço já existe. Parando e removendo..." -ForegroundColor Yellow
    if ($existingService.Status -eq 'Running') {
        Stop-Service -Name $serviceName -Force
    }
    sc.exe delete $serviceName
    Start-Sleep -Seconds 2
}

# Caminho completo do script Python
$mainScript = Join-Path $scriptDir "main.py"
if (-not (Test-Path $mainScript)) {
    Write-Host "ERRO: Arquivo main.py não encontrado em: $mainScript" -ForegroundColor Red
    exit 1
}

# Criar serviço usando sc.exe (Windows Service Control)
Write-Host "`nCriando serviço..." -ForegroundColor Yellow

$serviceDisplayName = "Xiaozhi MCP Bridge"
$serviceDescription = "Bridge MCP para conectar servidores MCP locais ao xiaozhi.me"

# Criar o serviço com diretório de trabalho correto
# Escapar corretamente os caminhos com espaços
$binPath = "cmd.exe /c `"cd /d `"$scriptDir`" && `"$pythonExe`" `"$mainScript`"`""

# Usar New-Service do PowerShell em vez de sc.exe para melhor tratamento de espaços
try {
    $service = New-Service -Name $serviceName `
        -BinaryPathName $binPath `
        -DisplayName $serviceDisplayName `
        -Description $serviceDescription `
        -StartupType Automatic `
        -ErrorAction Stop
    
    Write-Host "Serviço criado com sucesso!" -ForegroundColor Green
    
    # Configurar timeout de inicialização (padrão é 30s, vamos aumentar para 60s)
    $regPath = "HKLM:\SYSTEM\CurrentControlSet\Services\$serviceName"
    if (Test-Path $regPath) {
        # Aumentar timeout de inicialização para 60 segundos
        Set-ItemProperty -Path $regPath -Name "ServicesPipeTimeout" -Value 60000 -ErrorAction SilentlyContinue
        Write-Host "Timeout de inicialização configurado para 60 segundos." -ForegroundColor Green
    }
} catch {
    Write-Host "ERRO ao criar serviço: $_" -ForegroundColor Red
    Write-Host "Tentando método alternativo com sc.exe..." -ForegroundColor Yellow
    
    # Método alternativo: usar sc.exe com aspas corretas
    $binPathEscaped = $binPath -replace '"', '""'
    $result = & sc.exe create $serviceName "binPath= $binPathEscaped" "DisplayName= $serviceDisplayName" "start= auto"
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERRO ao criar serviço com sc.exe: $result" -ForegroundColor Red
        exit 1
    }
    
    # Configurar descrição separadamente
    & sc.exe description $serviceName $serviceDescription
    
    # Configurar timeout de inicialização
    $regPath = "HKLM:\SYSTEM\CurrentControlSet\Services\$serviceName"
    if (Test-Path $regPath) {
        Set-ItemProperty -Path $regPath -Name "ServicesPipeTimeout" -Value 60000 -ErrorAction SilentlyContinue
    }
}

# Configurar para executar no logon (start= auto já faz isso)
Write-Host "Serviço configurado para iniciar automaticamente no logon." -ForegroundColor Green
Write-Host "Diretório de trabalho: $scriptDir" -ForegroundColor Cyan

Write-Host "`n=== Serviço instalado com sucesso! ===" -ForegroundColor Green
Write-Host "Nome do serviço: $serviceName" -ForegroundColor Cyan
Write-Host "Display Name: $serviceDisplayName" -ForegroundColor Cyan
Write-Host "Iniciar automaticamente: Sim" -ForegroundColor Cyan
Write-Host "`nPara iniciar o serviço agora, execute:" -ForegroundColor Yellow
Write-Host "  Start-Service -Name $serviceName" -ForegroundColor White
Write-Host "`nPara verificar o status:" -ForegroundColor Yellow
Write-Host "  Get-Service -Name $serviceName" -ForegroundColor White
Write-Host "`nPara ver os logs:" -ForegroundColor Yellow
Write-Host "  Get-Content $scriptDir\bridge.log -Wait -Tail 20" -ForegroundColor White

