# Script para criar tarefa agendada do Windows para iniciar o bridge no logon
# Não requer privilégios de Administrador (mas funciona melhor com)

param(
    [switch]$Uninstall
)

$ErrorActionPreference = "Stop"

$taskName = "XiaozhiMCPBridge"
$scriptDir = Split-Path -Parent $PSScriptRoot
$pythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source

if (-not $pythonExe) {
    Write-Host "ERRO: Python não encontrado no PATH!" -ForegroundColor Red
    exit 1
}

Write-Host "Python encontrado: $pythonExe" -ForegroundColor Green
Write-Host "Diretório do projeto: $scriptDir" -ForegroundColor Cyan

if ($Uninstall) {
    Write-Host "`nRemovendo tarefa agendada $taskName..." -ForegroundColor Yellow
    
    $task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if ($task) {
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
        Write-Host "Tarefa removida com sucesso!" -ForegroundColor Green
    } else {
        Write-Host "Tarefa não encontrada." -ForegroundColor Yellow
    }
    exit 0
}

# Verificar se a tarefa já existe
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host "Tarefa já existe. Removendo..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Start-Sleep -Seconds 1
}

Write-Host "`n=== Criando Tarefa Agendada: $taskName ===" -ForegroundColor Green

# Criar ação (executar Python)
$action = New-ScheduledTaskAction -Execute $pythonExe -Argument "`"$scriptDir\main.py`"" -WorkingDirectory $scriptDir

# Criar trigger (ao fazer logon)
$trigger = New-ScheduledTaskTrigger -AtLogOn

# Criar configurações
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable:$false `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)

# Criar principal (executar como usuário atual)
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Highest

# Criar descrição
$description = "Xiaozhi MCP Bridge - Inicia automaticamente no logon do Windows"

try {
    # Registrar a tarefa
    Register-ScheduledTask `
        -TaskName $taskName `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Principal $principal `
        -Description $description `
        -Force
    
    Write-Host "`n✅ Tarefa agendada criada com sucesso!" -ForegroundColor Green
    Write-Host "Nome da tarefa: $taskName" -ForegroundColor Cyan
    Write-Host "Inicia automaticamente: Sim (no logon)" -ForegroundColor Cyan
    Write-Host "`nPara iniciar a tarefa agora, execute:" -ForegroundColor Yellow
    Write-Host "  Start-ScheduledTask -TaskName $taskName" -ForegroundColor White
    Write-Host "`nPara verificar o status:" -ForegroundColor Yellow
    Write-Host "  Get-ScheduledTask -TaskName $taskName" -ForegroundColor White
    Write-Host "`nPara ver os logs:" -ForegroundColor Yellow
    Write-Host "  Get-Content $scriptDir\bridge.log -Wait -Tail 20" -ForegroundColor White
    
} catch {
    Write-Host "`nERRO ao criar tarefa: $_" -ForegroundColor Red
    Write-Host "`nTentando método alternativo..." -ForegroundColor Yellow
    
    # Método alternativo usando schtasks.exe
    $schtasksCmd = "schtasks /Create /TN `"$taskName`" /TR `"`"$pythonExe`" `"$scriptDir\main.py`"`" /SC ONLOGON /RL HIGHEST /F"
    
    try {
        Invoke-Expression $schtasksCmd
        Write-Host "✅ Tarefa criada usando método alternativo!" -ForegroundColor Green
    } catch {
        Write-Host "ERRO: Não foi possível criar a tarefa." -ForegroundColor Red
        Write-Host "Tente executar como Administrador." -ForegroundColor Yellow
        exit 1
    }
}

