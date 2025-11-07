# Script PowerShell para verificar status da Bridge
# Uso: .\status_bridge.ps1

Write-Host "Status da Xiaozhi MCP Bridge" -ForegroundColor Cyan
Write-Host "=" * 50

$processes = Get-Process python -ErrorAction SilentlyContinue
if ($processes) {
    Write-Host "`nProcessos Python rodando:" -ForegroundColor Green
    $processes | Format-Table Id, ProcessName, StartTime, @{Label="Uptime"; Expression={(Get-Date) - $_.StartTime}} -AutoSize
    
    if (Test-Path bridge.log) {
        Write-Host "`nÚltimas linhas do log:" -ForegroundColor Cyan
        Get-Content bridge.log -Tail 10
    }
} else {
    Write-Host "`nNenhum processo Python encontrado" -ForegroundColor Yellow
    Write-Host "Bridge não está rodando" -ForegroundColor Red
}

Write-Host "`nVariável SSH_PASSWORD:" -ForegroundColor Cyan
if ($env:SSH_PASSWORD) {
    Write-Host "Configurada (oculta)" -ForegroundColor Green
} else {
    Write-Host "NÃO configurada" -ForegroundColor Red
}

